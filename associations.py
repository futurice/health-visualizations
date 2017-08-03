# encoding=utf-8
import json
import re
import io
import operator
import os
import sys
import itertools
import math
import csv
from random import shuffle
import editdistance as edt
import cPickle as pickle
import dosages 

# For adding to DB
from models import Drug, Symptom, Post, get_session, Bridge_Drug_Post, Bridge_Symptom_Post, get_db, Search_Term
from sqlalchemy.exc import IntegrityError

from progress_indicator import Progress_indicator


def ed(s1, s2):
    return edt.eval(s1, s2)

def out(*strings):
    print strings

def custom_split(words):
    words = words.replace('|','') # "kilo|metri" back to "kilometri"
    return re.split(' |\n|/|&', words) # Separate expressions such as "huimaus/väsymys"

def custom_split_stemmed(words):
    return custom_split(words.split('~')[1])
    
def custom_split_original(words):
    return custom_split(words.split('~')[0])

def read_special_words(file_path):
    words = set()
    with io.open(file_path) as file:
        file_contents = [x.strip() for x in file.readlines()]
        for word in file_contents:
            words.add(word)
            lastWord = word
    # Sanity check
    out(lastWord, " <<< should be the last word from ", file_path)
    return words

def compare_stems(stem1, stem2):
    a = len(stem1)
    b = len(stem2)
    if a != b:
        return a - b
    return a < b

def merge_stems(parents, stem1, stem2):
    # Find grandparents, merge longer into shorter
    while stem1 != parents[stem1]:
        stem1 = parents[stem1]
    while stem2 != parents[stem2]:
        stem2 = parents[stem2]
    if compare_stems(stem1, stem2) > 0:
        parents[stem1] = stem2
    else:
        parents[stem2] = stem1
    
def merge_similar(parents, words):
    # Iterate given set, merge similar words. Parents will be modified.
    word_list = list(words)
    end = len(words)
    for i, stem in enumerate(word_list):
        for j in range(i+1, end):
            stem2 = word_list[j]
            len1 = len(stem)
            len2 = len(stem2)
    
            # Merge stems which are substrings of each others' start
            # For longer stems also merge when editdistance=1 (SSRI != SNRI)
            if (len1 >= 6 and len2 >= 6 and ed(stem, stem2) == 1) \
            or (stem.startswith(stem2) or stem2.startswith(stem)):
                merge_stems(parents, stem, stem2)
                
def update_parenthood(parents, grandparents, words):
    # Update parents to point at grandparent, update grandparents
    for stem in words:
        parent = parents[stem]
        while parent != parents[parent]:
            parent = parents[parent]
        parents[stem] = parent
        grandparents.add(parent)
        

def map_abbreviations(grandparents, parents, vocab):
    for word in vocab:
        for stem in grandparents:
            if word.startswith(stem):
                parents[word] = parents[stem]
                #out("Mapping", word, parents[word])

def find_candidates(postCounts, grandparents, parents, db):
    representative_candidates = {}
    for parent in grandparents:
        postCounts[parent] = 0
    for post in db.query(Post):
        seenInPost = set()
        for child in custom_split(post.lemmatized):
            parent = parents[child]
            if parent not in grandparents:
                continue # Word does not represent a drug/symptom
            if parent in seenInPost:
                continue # Already counted this word for this post
            postCounts[parent] += 1
            seenInPost.add(parent)

            # Each stem is represented by its most common occurrence
            if parent not in representative_candidates:
                representative_candidates[parent] = {}
            count = 1
            if child in representative_candidates[parent]:
                count += representative_candidates[parent][child]
            representative_candidates[parent][child] = count
    return representative_candidates

def find_representatives(candidates, grandparents):
    representatives = {}
    for parent in grandparents:
        if parent not in candidates:
            representatives[parent] = parent
            continue
        for child in candidates[parent]:
            val_highest = 0
            child_highest = ''
            for child, val in candidates[parent].iteritems():
                if val > val_highest:
                    val_highest = val
                    child_highest = child
            representatives[parent] = child_highest
    return representatives

def collect_postSets(parents, grandparents, db):
    postSets = {} # key = drug/symptom, value = set of posts
    for word in grandparents:
        postSets[word] = set()
    for post in db.query(Post):
        post_keys = set()
        for child in custom_split(post.lemmatized):
            parent = parents[child]
            if parent not in grandparents:
                continue # Word does not represent a drug/symptom
            post_keys.add(parent)
        for key in post_keys:
            postSets[key].add(post)
    return postSets

# Iterate posts with keyword, count associations
def count_associations(keyword, parents, grandparents, postSets):
    counts = {}
    for parent in grandparents:
        counts[parent] = 0
    for post in postSets[keyword]:
        seen_in_post = set()
        for child in custom_split(post.lemmatized):
            parent = parents[child]
            if parent not in grandparents:
                continue # Word does not represent a drug
            if parent in seen_in_post:
                continue # Already counted for this post
            seen_in_post.add(parent)
            count = 1
            if parent not in counts:
                counts[parent] = {}
            else:
                count += counts[parent]
            counts[parent] = count
    return counts


    """ Returns baskets of abbreviations for each keyword in grandparents set. """
def get_baskets(db, parents, grandparents):
    baskets = dict()

    # Finnish-Dep-Parser sometimes lemmatizes "novia" into "novia", sometimes into "nova".
    # Furthermore, these lemmatized forms end up with different parents (themselves).
    # This makes it ambiguous which parent is referred to with potential search term "novia".
    # Since it's just this 1 case, we will print a warning and arbitrarily add it into 1 basket only.
    seen_search_terms = dict()

    for keyword in grandparents:
        baskets[keyword] = set()

    for post in db.query(Post).all():
        # First split by space, then split elements individually by custom split function.
        # Do not refactor the space split away (Finnish-Dep-Parser does weird things to long words,
        # causing custom split to return different lengths to original and lemmatized versions of post)
        i = -1
        original_elements = post.original.split(' ')
        lemmatized_elements = post.lemmatized.split(' ')
        for orig_element in original_elements:
            i += 1
            lemm_element = lemmatized_elements[i]

            original_words_of_element = custom_split(orig_element)
            lemmatized_words_of_element = custom_split(lemm_element)

            # Original "words of element" may be longer than lemmatized "words of element".
            # Iterate lemmatized words and skip any additional "original words of element".
            # Example why this parsing is necessary:
            #   Original element: lehtihaku_view_article_war_dlehtihaku&amp;p_p_action=1&amp;p_p_state=maximized
            #   Lemmatized element: lehtihaku_view_article_war_dle-(((31)))-maximized
            #   If we simply called custom_split on original post and lemmatized post, the splits would
            #   yield different lengths (due to splitting by '&' character, in this example). Then it would
            #   not be possible to say which original word corresponds to which lemmatized word.
            j = -1
            for lemm_word in lemmatized_words_of_element:
                j += 1
                orig_word = original_words_of_element[j]
                parent = parents[lemm_word]
                if parent in grandparents:
                    if lemm_word not in seen_search_terms:
                        baskets[parent].add(lemm_word)
                        seen_search_terms[lemm_word] = parent
                    elif parent != seen_search_terms[lemm_word]:
                        print 'Ambiguous search term', lemm_word, 'has 2 parents', parent, 'and', seen_search_terms[lemm_word]
                    if orig_word not in seen_search_terms:
                        baskets[parent].add(orig_word)
                        seen_search_terms[lemm_word] = parent
                    elif parent != seen_search_terms[orig_word]:
                        print 'Ambiguous search term', orig_word, 'has 2 parents', parent, 'and', seen_search_terms[orig_word]

    return baskets
            
def calculate_bp(grandparents, postSets, counts, postCounts, keyword, number_of_posts, minimum_sample_size_for_found_associations):
    # Bayesian probability: calculate how much 'keyword' increases the prevalence of special words
    bp = {}
    for parent in grandparents:
        freq_all = 1.0 * postCounts[parent] / number_of_posts
        freq_assoc = 1.0 * counts[parent] / len(postSets[keyword])

        if freq_all == 0 \
        or freq_assoc < freq_all \
        or counts[parent] < minimum_sample_size_for_found_associations:
            continue
        bp[parent] = (100 * freq_assoc / freq_all) - 100
    # We don't want to plot the keyword itself 
    if keyword in bp:
        del bp[keyword]
    return bp

def filter_nonexisting_grandparents(parents, grandparents, vocab):
    # We may have grandparents which do not appear in the data
    # because the data is lemmatized whereas some drugs/symptoms
    # may not be lemmatized. This returns a new grandparents
    # set with only grandparents which appear in the data.
    found_grandparents = set()
    for word in vocab:
        found_grandparents.add(parents[word])
    filtered_grandparents = set()
    for candidate in grandparents:
        if candidate in found_grandparents:
            filtered_grandparents.add(candidate)
    return filtered_grandparents

class Associations:
    def __init__(self, data_file, symptoms_file, drugs_file):
        self.data_file = data_file
        self.symptoms_file = symptoms_file
        self.drugs_file = drugs_file

    def train(self, db):
        out('Producing associations object...')

        self.vocab = set()
        self.number_of_posts = db.query(Post).count()
        for post in db.query(Post):
            for word in custom_split(post.lemmatized):
                self.vocab.add(word)

        out('Part 0 done: vocabulary size', len(self.vocab))

        drugs = read_special_words(self.drugs_file)
        symptoms = read_special_words(self.symptoms_file)

        # Initialization
        self.drug_grandparents = set()
        self.drug_parents = {}
        self.symptom_grandparents = set()
        self.symptom_parents = {}
        for word in itertools.chain(*[self.vocab, drugs, symptoms]):
            # drugs and symptoms contain stemmed words which don't appear in the corpus
            self.drug_parents[word] = word
            self.symptom_parents[word] = word

        # Actual work
        merge_similar(self.drug_parents, drugs)
        update_parenthood(self.drug_parents, self.drug_grandparents, drugs)
        merge_similar(self.symptom_parents, symptoms)
        update_parenthood(self.symptom_parents, self.symptom_grandparents, symptoms)
        out('Part 1 done: merged similar special words')

        self.drug_grandparents = filter_nonexisting_grandparents(self.drug_parents, self.drug_grandparents, self.vocab)
        self.symptom_grandparents = filter_nonexisting_grandparents(self.symptom_parents, self.symptom_grandparents, self.vocab)

        # Mapping full vocabulary to known drug stems doesn't appear to cause too many false positives
        map_abbreviations(self.drug_grandparents, self.drug_parents, self.vocab)            

        # Mapping full vocabulary to symptoms by using startswith(stem) provides too many false positives!
        # Instead, let's rely on finnish-dep-parser's lemmatization for symptoms
        #map_abbreviations(self.symptom_grandparents, self.symptom_grandparents)
        out('Part 2 done: merged full vocabulary')

        self.drug_postCounts = {}
        drug_rep_candidates = find_candidates(self.drug_postCounts, self.drug_grandparents, self.drug_parents, db)
        self.drug_representatives = find_representatives(drug_rep_candidates, self.drug_grandparents)
        self.symptom_postCounts = {}
        symptom_rep_candidates = find_candidates(self.symptom_postCounts, self.symptom_grandparents, self.symptom_parents, db)
        self.symptom_representatives = find_representatives(symptom_rep_candidates, self.symptom_grandparents)
        out('Part 3 done: postcounts and representatives')

        self.drug_postSets = collect_postSets(self.drug_parents, self.drug_grandparents, db)
        self.symptom_postSets = collect_postSets(self.symptom_parents, self.symptom_grandparents, db)
        out("Part 4 done: collected postsets")

        self.drug_baskets = get_baskets(db, self.drug_parents, self.drug_grandparents)
        self.symptom_baskets = get_baskets(db, self.symptom_parents, self.symptom_grandparents)
        out("Part 5 done: collected baskets")

    def calculate_dosages(self, db):
        #if not 'drug_dosages' in locals():
        d = dosages.Dosages(self.drug_parents, self.drug_grandparents, self.drug_representatives)
        self.drug_dosages = d.train(db)

    # Returns associated (drugs, drug_counts, symptoms, symptom_counts)
    def associated(self, keyword, minimum_sample_size_for_found_associations=1):
        if self.drug_parents[keyword] in self.drug_grandparents:
            out('Keyword recognized as drug', self.drug_representatives[self.drug_parents[keyword]])
            keyword = self.drug_parents[keyword]
            keyword_representative = self.drug_representatives[keyword]
            selected_postSets = self.drug_postSets
        elif self.symptom_parents[keyword] in self.symptom_grandparents:
            out('Keyword recognized as symptom', self.symptom_representatives[self.symptom_parents[keyword]])
            keyword = self.symptom_parents[keyword]
            keyword_representative = self.symptom_representatives[keyword]
            selected_postSets = self.symptom_postSets
        else:
            raise Exception('Keyword not recognized as a drug or symptom: ' + keyword)

        drug_counts = count_associations(keyword, self.drug_parents, self.drug_grandparents, selected_postSets)
        symptom_counts = count_associations(keyword, self.symptom_parents, self.symptom_grandparents, selected_postSets)

        drug_bp = calculate_bp(self.drug_grandparents, selected_postSets, drug_counts, self.drug_postCounts, keyword, self.number_of_posts, minimum_sample_size_for_found_associations)
        symptom_bp = calculate_bp(self.symptom_grandparents, selected_postSets, symptom_counts, self.symptom_postCounts, keyword, self.number_of_posts, minimum_sample_size_for_found_associations)
        return (drug_bp, drug_counts, symptom_bp, symptom_counts)

""" Create associations JSON for database for resource e.g "drugs" """
def create_json(db, resource_name, grandparents, baskets, representatives,  post_counts):

    for resource in grandparents:
        created_json = dict()
        real_name = representatives[resource]
        drug_assoc, drug_counts, symptom_assoc, symptom_counts = a.associated(resource)
        
        associated_drugs = dict()
        associated_symptoms = dict()

        for assoc_drug, value in drug_assoc.iteritems():
            rn = a.drug_representatives[assoc_drug]

            associated_drugs[rn] = {
                "value": value,
                "count": drug_counts[assoc_drug]
            }

        for assoc_symptom, value in symptom_assoc.iteritems():
            rn = a.symptom_representatives[assoc_symptom]
            associated_symptoms[rn] = {
                "value": value,
                "count": symptom_counts[assoc_symptom]
            }

        created_json["associated_drugs"] = associated_drugs
        created_json["associated_symptoms"] = associated_symptoms
        created_json["basket"] = list(baskets[resource])

        post_count = post_counts[resource]
        created_json["postCount"] = post_count

        if resource_name == "drugs":
            # Dosages will be calculated later
            '''
            if real_name in a.drug_dosages:
                created_json["dosages"] = a.drug_dosages[real_name]
            else:
                created_json["dosages"] = {}
            '''
            res = Drug(name=real_name, data=created_json)
        elif resource_name == "symptoms":
            res = Symptom(name = real_name, data=created_json)
        try:
            db.add(res)
            db.commit()
        except IntegrityError:
            print "Already exists"


def insert_posts_into_db(db, data_json_path):
    print 'Loading', data_json_path
    with open(data_json_path) as file:
        data = json.load(file)
    print 'Done.'
    progress_indicator = Progress_indicator(len(data))
    csv_file_path = os.path.abspath('/tmp/temp.csv')
    with open(csv_file_path, 'wb') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter='~', lineterminator='\n')
        csv_writer.writerow(['id', 'original_post', 'lemmatized_post'])
        next_free_id = 1
        for thread in data:
            progress_indicator.tick()
            for post in thread:
                original_post = post.split('~')[0]
                lemmatized_post = post.split('~')[1]

                # This is too slow, instead write to CSV and then copy CSV into postgres with raw SQL
                # db.add(Post(original=original_post, lemmatized=lemmatized_post))
                # db.commit()

                csv_writer.writerow([next_free_id, original_post.encode("utf-8"), lemmatized_post.encode("utf-8")])
                next_free_id += 1

    print csv_file_path

    db.execute("COPY posts FROM '" + csv_file_path + "' DELIMITER '~' CSV HEADER;")
    db.commit()

def load_pickle():
    print "Loading pickled associations"
    f = open(pickled_path)
    return pickle.load(f)

def save_pickle():
    print "Saving pickled associations"
    f = open(pickled_path, 'w')
    pickle.dump(a, f)

if __name__ == "__main__":
    db = get_session()
    processed_data_folder = os.path.join('..', 'how-to-get-healthy', 'processed_data')
    word_lists_folder = os.path.join('..', 'how-to-get-healthy', 'word_lists')
    data_json_path = os.path.join(processed_data_folder, 'data.json')
    drugs_path = os.path.join(word_lists_folder, 'drugs_stemmed.txt')
    symptom_path = os.path.join(word_lists_folder, 'symptoms_both_ways_stemmed.txt')
    pickled_path = "associations_object"

    print "If you are running this for the first time, just enter \"y\" on everything."
    insert_posts = raw_input("Insert posts from data.json to db? Be wary of inserting duplicates. Enter y/n: ")
    insert_drugs_symptoms = raw_input("Insert drugs and symptoms to db? Enter y/n: ")
    insert_dosages = raw_input("Insert dosages to db? Enter y/n: ")
    insert_postset_bridges = raw_input("Insert postset bridges to db? Enter y/n: ")
    insert_search_terms = raw_input("Insert search terms to db? Enter y/n: ")
    recreate_pickle = raw_input("Recreate pickled associations object? Enter y/n: ")

    if insert_posts == "y":
        insert_posts_into_db(db, data_json_path)

    if recreate_pickle == "y" or not os.path.isfile(pickled_path):
        a = Associations(data_json_path, symptom_path, drugs_path)
        a.train(db)
        save_pickle()
    else:
        a = load_pickle()

        
    # Associations
    if insert_drugs_symptoms == "y":
        create_json(db, "symptoms", a.symptom_grandparents, a.symptom_baskets, a.symptom_representatives, a.symptom_postCounts)
        create_json(db, "drugs", a.drug_grandparents, a.drug_baskets, a.drug_representatives, a.drug_postCounts)

    # Dosages
    if insert_dosages == "y":
        a.calculate_dosages(db)
        save_pickle()

    # Postset bridges to db
    if insert_postset_bridges == "y":
        print 'Inserting postset bridges to db...'

        progress_indicator = Progress_indicator(len(a.drug_postSets))
        csv_file_path = os.path.abspath('/tmp/temp3.csv')
        with open(csv_file_path, 'wb') as csvfile:
            csv_writer = csv.writer(csvfile, delimiter='~', lineterminator='\n')
            csv_writer.writerow(['id', 'post_id', 'drug_id'])
            next_free_id = 1
            for grandparent in a.drug_postSets:
                progress_indicator.tick()
                drug = db.query(Drug).filter(Drug.name == a.drug_representatives[grandparent]).one()
                for post in a.drug_postSets[grandparent]:
                    # Too slow
                    #db.add(Bridge_Drug_Post(post_id=post.id, drug_id=drug.id))
                    csv_writer.writerow([next_free_id, post.id, drug.id])
                    next_free_id += 1
        db.execute("COPY bridge_drug_posts FROM '" + csv_file_path + "' DELIMITER '~' CSV HEADER;")
        db.commit()

        progress_indicator = Progress_indicator(len(a.symptom_postSets))
        csv_file_path = os.path.abspath('/tmp/temp4.csv')
        with open(csv_file_path, 'wb') as csvfile:
            csv_writer = csv.writer(csvfile, delimiter='~', lineterminator='\n')
            csv_writer.writerow(['id', 'post_id', 'symptom_id'])
            next_free_id = 1
            for grandparent in a.symptom_postSets:
                progress_indicator.tick()
                symptom = db.query(Symptom).filter(Symptom.name == a.symptom_representatives[grandparent]).one()
                for post in a.symptom_postSets[grandparent]:
                    # Too slow
                    # db.add(Bridge_Symptom_Post(post_id=post.id, symptom_id=symptom.id))
                    csv_writer.writerow([next_free_id, post.id, symptom.id])
                    next_free_id += 1
        db.execute("COPY bridge_symptom_posts FROM '" + csv_file_path + "' DELIMITER '~' CSV HEADER;")
        db.commit()

    # Search terms to db
    seen_search_terms = set()
    if insert_search_terms == "y":
        for drug in db.query(Drug).all():
            for term in drug.data["basket"]:
                if len(term) > 64:
                    # This table exists to help user searches. Assuming users don't need to search with super long terms.
                    continue
                db.add(Search_Term(name=term, drug_id=drug.id, symptom_id=None))
                db.commit()
        for symptom in db.query(Symptom).all():
            for term in symptom.data["basket"]:
                if len(term) > 64:
                    continue
                db.add(Search_Term(name=term, drug_id=None, symptom_id=symptom.id))
                db.commit()