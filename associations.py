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
from models import initialize_db, create_indexes

# For adding to DB
from models import (
    Drug, Symptom, Post, Bridge_Drug_Post, Bridge_Symptom_Post,
    Search_Term, db
)
from services import db_session
from sqlalchemy.exc import IntegrityError

from progress_indicator import Progress_indicator


def get_edit_distance(s1, s2):
    return edt.eval(s1, s2)

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
    print lastWord, " <<< should be the last word from ", file_path
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
            if (len1 >= 6 and len2 >= 6 and get_edit_distance(stem, stem2) == 1) \
            or (stem.startswith(stem2) or stem2.startswith(stem)):
                merge_stems(parents, stem, stem2)

def update_parenthood(parents, words):
    # Update parents to point at grandparent
    for stem in words:
        parent = parents[stem]
        while parent != parents[parent]:
            parent = parents[parent]
        parents[stem] = parent

def collect_grandparents(parents, words):
    grandparents = set()
    for stem in words:
        grandparents.add(parents[stem])
    return grandparents

def map_abbreviations(grandparents, parents, vocab):
    for word in vocab:
        for stem in grandparents:
            if word.startswith(stem):
                parents[word] = parents[stem]
                #out("Mapping", word, parents[word])

def find_candidates(post_counts, grandparents, parents, db):
    representative_candidates = {}
    for parent in grandparents:
        post_counts[parent] = 0
    for post in db.query(Post):
        seenInPost = set()
        for child in custom_split(post.lemmatized):
            parent = parents[child]
            if parent not in grandparents:
                continue # Word does not represent a drug/symptom
            if parent in seenInPost:
                continue # Already counted this word for this post
            post_counts[parent] += 1
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

def collect_post_sets(parents, grandparents, db):
    post_sets = {} # key = drug/symptom, value = set of posts
    for word in grandparents:
        post_sets[word] = set()
    for post in db.query(Post):
        post_keys = set()
        for child in custom_split(post.lemmatized):
            parent = parents[child]
            if parent not in grandparents:
                continue # Word does not represent a drug/symptom
            post_keys.add(parent)
        for key in post_keys:
            post_sets[key].add(post)
    return post_sets

# Iterate posts with keyword, count associations
def count_associations(keyword, parents, grandparents, post_sets):
    counts = {}
    for parent in grandparents:
        counts[parent] = 0
    for post in post_sets[keyword]:
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


# Helper class to match lemmatized words to their respective original word
class Word_Matcher():
    def __init__(self, post):
        self.original = []
        self.lemmatized = []

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
                self.original.append(orig_word)
                self.lemmatized.append(lemm_word)

    """ Returns baskets of abbreviations for each keyword in grandparents set. """
def get_baskets(db, parents, grandparents):
    baskets = dict()

    for keyword in grandparents:
        baskets[keyword] = set()

    for post in db.query(Post).all():
        matcher = Word_Matcher(post)
        for i in range(len(matcher.lemmatized)):
            lemm_word = matcher.lemmatized[i]
            orig_word = matcher.original[i]
            parent = parents[lemm_word]
            if parent in grandparents:
                baskets[parent].add(lemm_word)
                baskets[parent].add(orig_word)

    return baskets

# Note: do not refactor "parent_curr" parameter away -- word can be original word,
# in which case parent should still be the parent of the lemmatized version,
# not the parent of the original version!
def fix_potential_ambiguity_for_word(word, parent_curr, parents, seen):
    if word not in seen:
        seen[word] = parent_curr
        return
    parent_prev = seen[word]
    if parent_curr != parent_prev:
        merge_stems(parents, parent_curr, parent_prev)

# Finnish-Dep-Parser sometimes lemmatizes "kivut" into "kipu", sometimes into "kivut".
# Furthermore, these lemmatized forms end up with different parents (themselves).
# Setting aside the fact that these buckets should be merged, there is a bigger problem:
# When a user searches with term "kivut", it's ambiguous which bucket we should return.
# This function solves this problem by merging the grandparents of ambiguous terms.
def merge_ambiguous_lemmatizations(db, parents, grandparents):
    seen = {}
    for post in db.query(Post).all():
        matcher = Word_Matcher(post)
        for i in range(len(matcher.lemmatized)):
            lemm_word = matcher.lemmatized[i]
            orig_word = matcher.original[i]

            # Find grandparent of lemm_word.
            parent = parents[lemm_word]
            while parent != parents[lemm_word]:
                # Note: do not refactor the while loop away,
                # it CAN activate in cases where we merge stuff as we iterate posts.
                parent = parents[lemm_word]

            if parent not in grandparents:
                # Not a drug/symptom word.
                continue

            # Check ambiguity for both both lemm_word and orig_word, merge ambiguous words.
            fix_potential_ambiguity_for_word(lemm_word, parent, parents, seen)
            fix_potential_ambiguity_for_word(orig_word, parent, parents, seen)


def calculate_lift(grandparents, post_sets, counts, post_counts, keyword, number_of_posts, minimum_sample_size_for_found_associations):
    # How much 'keyword' increases the prevalence of special words
    lift = {}
    for parent in grandparents:
        freq_all = 1.0 * post_counts[parent] / number_of_posts
        freq_assoc = 1.0 * counts[parent] / len(post_sets[keyword])

        if freq_all == 0 \
        or freq_assoc < freq_all \
        or counts[parent] < minimum_sample_size_for_found_associations:
            continue
        lift[parent] = (100 * freq_assoc / freq_all) - 100
    # We don't want to plot the keyword itself
    if keyword in lift:
        del lift[keyword]
    return lift

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
    def __init__(self, symptoms_file, drugs_file):
        self.symptoms_file = symptoms_file
        self.drugs_file = drugs_file

    def update_all_parents_and_grandparents(self):
        update_parenthood(self.drug_parents, self.drug_words)
        update_parenthood(self.symptom_parents, self.symptom_words)
        self.drug_grandparents = collect_grandparents(self.drug_parents, self.drug_words)
        self.symptom_grandparents = collect_grandparents(self.symptom_parents, self.symptom_words)

    def train(self, db):
        print 'Producing associations object...'

        self.vocab = set()
        self.number_of_posts = db.query(Post).count()
        for post in db.query(Post):
            for word in custom_split(post.lemmatized):
                self.vocab.add(word)

        print 'Part 0 done: vocabulary size', len(self.vocab)

        self.drug_words = read_special_words(self.drugs_file)
        self.symptom_words = read_special_words(self.symptoms_file)

        # Initialization
        self.drug_parents = {}
        self.symptom_parents = {}
        for word in itertools.chain(*[self.vocab, self.drug_words, self.symptom_words]):
            # Note that drugs and symptoms may contain stemmed words which don't appear in the corpus
            self.drug_parents[word] = word
            self.symptom_parents[word] = word

        # Merge similar drug words into each other, same with symptom words separately
        merge_similar(self.drug_parents, self.drug_words)
        merge_similar(self.symptom_parents, self.symptom_words)

        # Update parents and grandparents before merging ambiguous lemmatizations
        self.update_all_parents_and_grandparents()

        # Merge ambiguous lemmatizations
        merge_ambiguous_lemmatizations(db, self.drug_parents, self.drug_grandparents)
        merge_ambiguous_lemmatizations(db, self.symptom_parents, self.symptom_grandparents)

        # We need these updates after the merge as well
        self.update_all_parents_and_grandparents()

        print 'Part 1 done: merged similar special words'

        self.drug_grandparents = filter_nonexisting_grandparents(self.drug_parents, self.drug_grandparents, self.vocab)
        self.symptom_grandparents = filter_nonexisting_grandparents(self.symptom_parents, self.symptom_grandparents, self.vocab)

        # Mapping full vocabulary to known drug stems doesn't appear to cause too many false positives
        map_abbreviations(self.drug_grandparents, self.drug_parents, self.vocab)

        # Mapping full vocabulary to symptoms by using startswith(stem) provides too many false positives!
        # Instead, let's rely on finnish-dep-parser's lemmatization for symptoms
        #map_abbreviations(self.symptom_grandparents, self.symptom_grandparents)
        print 'Part 2 done: merged full vocabulary'

        self.drug_post_counts = {}
        drug_rep_candidates = find_candidates(self.drug_post_counts, self.drug_grandparents, self.drug_parents, db)
        self.drug_representatives = find_representatives(drug_rep_candidates, self.drug_grandparents)
        self.symptom_post_counts = {}
        symptom_rep_candidates = find_candidates(self.symptom_post_counts, self.symptom_grandparents, self.symptom_parents, db)
        self.symptom_representatives = find_representatives(symptom_rep_candidates, self.symptom_grandparents)
        print 'Part 3 done: postcounts and representatives'

        self.drug_post_sets = collect_post_sets(self.drug_parents, self.drug_grandparents, db)
        self.symptom_post_sets = collect_post_sets(self.symptom_parents, self.symptom_grandparents, db)
        print "Part 4 done: collected postsets"

        self.drug_baskets = get_baskets(db, self.drug_parents, self.drug_grandparents)
        self.symptom_baskets = get_baskets(db, self.symptom_parents, self.symptom_grandparents)
        print "Part 5 done: collected baskets"

    # Returns associated (drugs, drug_counts, symptoms, symptom_counts)
    def associated(self, keyword, minimum_sample_size_for_found_associations=1):
        if self.drug_parents[keyword] in self.drug_grandparents:
            print 'Keyword recognized as drug', self.drug_representatives[self.drug_parents[keyword]]
            keyword = self.drug_parents[keyword]
            keyword_representative = self.drug_representatives[keyword]
            selected_post_sets = self.drug_post_sets
        elif self.symptom_parents[keyword] in self.symptom_grandparents:
            print 'Keyword recognized as symptom', self.symptom_representatives[self.symptom_parents[keyword]]
            keyword = self.symptom_parents[keyword]
            keyword_representative = self.symptom_representatives[keyword]
            selected_post_sets = self.symptom_post_sets
        else:
            raise Exception('Keyword not recognized as a drug or symptom: ' + keyword)

        drug_counts = count_associations(keyword, self.drug_parents, self.drug_grandparents, selected_post_sets)
        symptom_counts = count_associations(keyword, self.symptom_parents, self.symptom_grandparents, selected_post_sets)

        drug_lift = calculate_lift(self.drug_grandparents, selected_post_sets, drug_counts, self.drug_post_counts, keyword, self.number_of_posts, minimum_sample_size_for_found_associations)
        symptom_lift = calculate_lift(self.symptom_grandparents, selected_post_sets, symptom_counts, self.symptom_post_counts, keyword, self.number_of_posts, minimum_sample_size_for_found_associations)
        return (drug_lift, drug_counts, symptom_lift, symptom_counts)

'''
Example call parameters: (db_session, a.drug_representatives, a.drug_postsets, Drug, 'bridge_drug_posts', 'drug_id')
For performance reasons we write to file and then use Postgres COPY to import that file.
(Directly inserting rows into the database 1 by 1 took forever)
'''
def populate_postset_bridges(db, representatives, post_sets, entity_class, table_name, id_type):

    if len(db.query(table_name).limit(1).all()) > 0:
        print entity_class, 'table is not empty - skipping'
        return
    else:
        print '\n\nPopulating', table_name, 'table...'

    progress_indicator = Progress_indicator(len(post_sets))
    csv_file_path = os.path.abspath('/tmp/temp_' + table_name + '.csv')
    with open(csv_file_path, 'wb') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter='~', lineterminator='\n')
        csv_writer.writerow(['id', 'post_id', id_type])
        next_free_id = 1
        for grandparent in post_sets:
            progress_indicator.tick()
            entity = db.query(entity_class).filter(entity_class.name == representatives[grandparent]).one()
            for post in post_sets[grandparent]:
                csv_writer.writerow([next_free_id, post.id, entity.id])
                next_free_id += 1
    db.execute("COPY " + table_name + " FROM '" + csv_file_path + "' DELIMITER '~' CSV HEADER;")
    db.commit()

def write_search_terms_to_csv(db, csv_writer, entity_class, next_free_id):
    entities = db.query(entity_class).all()
    progress_indicator = Progress_indicator(len(entities))
    for entity in entities:
        progress_indicator.tick()
        for term in entity.data["basket"]:
            if len(term) > 64:
                # Users don't need to search with super long terms, db column limited to 64 chars.
                continue
            drug_id = 'None'
            symptom_id = 'None'
            if entity_class == Drug:
                drug_id = entity.id
            else:
                symptom_id = entity.id
            csv_writer.writerow([next_free_id, term.encode("utf-8"), drug_id, symptom_id])
            next_free_id += 1
    return next_free_id

def populate_search_terms(db):
    if len(db.query(Search_Term).limit(1).all()) > 0:
        print 'Search_Terms table is not empty - skipping'
        return
    else:
        print '\n\nPopulating Search_Terms table...'

    csv_file_path = os.path.abspath('/tmp/temp_search_terms.csv')
    with open(csv_file_path, 'wb') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter='~', lineterminator='\n')
        csv_writer.writerow(['id', 'name', 'drug_id', 'symptom_id'])
        next_free_id = 1
        next_free_id = write_search_terms_to_csv(db, csv_writer, Drug, next_free_id)
        next_free_id = write_search_terms_to_csv(db, csv_writer, Symptom, next_free_id)
    db.execute("COPY search_terms FROM '" + csv_file_path + "' DELIMITER '~' NULL as 'None' CSV HEADER;")
    db.commit()

""" Create associations JSON for database for resource e.g "drugs" """
def populate_drugs_or_symptoms(db, entity_class, grandparents, baskets, representatives, post_counts):

    if len(db.query(entity_class).limit(1).all()) > 0:
        print entity_class, 'table is not empty - skipping'
        return
    else:
        print '\n\nPopulating', entity_class, 'table...'

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
        created_json["post_count"] = post_count

        if entity_class == Drug:
            # Note: dosages will be calculated later and this field will be updated.
            res = Drug(name=real_name, data=created_json)
        elif entity_class == Symptom:
            res = Symptom(name = real_name, data=created_json)
        try:
            db.add(res)
            db.commit()
        except IntegrityError:
            print "Already exists"


def populate_posts(db, data_json_path):
    if len(db.query(Post).limit(1).all()) > 0:
        print 'Posts table is not empty - skipping'
        return
    else:
        print '\n\nPopulating posts table...'

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
                csv_writer.writerow([next_free_id, original_post.encode("utf-8"), lemmatized_post.encode("utf-8")])
                next_free_id += 1
    db.execute("COPY posts FROM '" + csv_file_path + "' DELIMITER '~' CSV HEADER;")
    db.commit()


if __name__ == "__main__":
    with db_session(db) as session:
        processed_data_folder = os.path.join('..', 'how-to-get-healthy', 'processed_data')
        word_lists_folder = os.path.join('..', 'how-to-get-healthy', 'word_lists')
        data_json_path = os.path.join(processed_data_folder, 'data.json')
        drugs_path = os.path.join(word_lists_folder, 'drugs_stemmed.txt')
        symptom_path = os.path.join(word_lists_folder, 'symptoms_both_ways_stemmed.txt')

        initialize_db()

        raw_input("We will populate any tables which are empty, then we will create indexes. Press enter to continue.")

        # Posts must be populated first
        populate_posts(session, data_json_path)

        # Precalculate stuff to make later steps faster
        a = Associations(symptom_path, drugs_path)
        a.train(session)

        # Drugs and symptoms must be inserted to db before calculating dosages
        populate_drugs_or_symptoms(session, Symptom, a.symptom_grandparents, a.symptom_baskets, a.symptom_representatives, a.symptom_post_counts)
        populate_drugs_or_symptoms(session, Drug, a.drug_grandparents, a.drug_baskets, a.drug_representatives, a.drug_post_counts)

        # Calculate dosages; populate bridge_dosage_quotes and update drugs.data to include dosages
        d = dosages.Dosages(a.drug_parents, a.drug_grandparents, a.drug_representatives)
        a.drug_dosages = d.populate(session)

        # Populate postset bridges and search term tables
        populate_postset_bridges(session, a.drug_representatives, a.drug_post_sets, Drug, 'bridge_drug_posts', 'drug_id')
        populate_postset_bridges(session, a.symptom_representatives, a.symptom_post_sets, Symptom, 'bridge_symptom_posts', 'symptom_id')
        populate_search_terms(session)

        create_indexes(confirm=True)