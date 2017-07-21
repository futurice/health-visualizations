# encoding=utf-8
import json
import re
import io
import operator
import os
import sys
import itertools
import math
from random import shuffle
import editdistance as edt
import cPickle as pickle
import dosages 

# For adding to DB
from models import Drug, Symptom, get_session
from sqlalchemy.exc import IntegrityError

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

def find_candidates(postCounts, grandparents, parents, data):
    representative_candidates = {}
    for parent in grandparents:
        postCounts[parent] = 0
    for thread in data:
        for post in thread:
            seenInPost = set()
            for child in custom_split_stemmed(post):
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

def collect_postSets(parents, grandparents, data):
    postSets = {} # key = drug/symptom, value = set of posts
    for word in grandparents:
        postSets[word] = set()
    for thread in data:
        for post in thread:
            post_keys = set()
            for child in custom_split_stemmed(post):
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
        for child in custom_split_stemmed(post):
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


    """ Takes whole vocab and wanted keywords, e.g drugs, and returns sets of words for each keyword """
def get_baskets(vocab, parents, grandparents):
    baskets = dict()

    for keyword in grandparents:
        baskets[keyword] = set()

    for word in vocab:
        p = parents[word]
        if p in grandparents:
            baskets[p].add(word)

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

    def train(self):
        out('Producing associations object...')
        with open(self.data_file) as file:
            self.data = json.load(file)
        self.vocab = set()
        self.number_of_posts = 0
        for thread in self.data:
            for post in thread:
                self.number_of_posts += 1
                for word in custom_split_stemmed(post):
                    self.vocab.add(word)
        out('Part 0 done.')

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
        drug_rep_candidates = find_candidates(self.drug_postCounts, self.drug_grandparents, self.drug_parents, self.data)
        self.drug_representatives = find_representatives(drug_rep_candidates, self.drug_grandparents)
        self.symptom_postCounts = {}
        symptom_rep_candidates = find_candidates(self.symptom_postCounts, self.symptom_grandparents, self.symptom_parents, self.data)
        self.symptom_representatives = find_representatives(symptom_rep_candidates, self.symptom_grandparents)
        out('Part 3 done: postcounts and representatives')

        self.drug_postSets = collect_postSets(self.drug_parents, self.drug_grandparents, self.data)
        self.symptom_postSets = collect_postSets(self.symptom_parents, self.symptom_grandparents, self.data)
        out("Part 4 done: collected postsets")

        self.drug_baskets = get_baskets(self.vocab, self.drug_parents, self.drug_grandparents)
        self.symptom_baskets = get_baskets(self.vocab, self.symptom_parents, self.symptom_grandparents)
        out("Part 5 done: collected baskets")

        # Find dosage information
        if not 'drug_dosages' in locals():
            d = dosages.Dosages(self.data, self.drug_parents, self.drug_grandparents, self.drug_representatives)
            self.drug_dosages = d.train()

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
def create_json(resource_name, grandparents, baskets, representatives,  post_counts):
    db_session = get_session()

    for resource in grandparents:
        created_json = dict()
        print "Processing", resource
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
            if real_name in a.drug_dosages:
                created_json["dosages"] = a.drug_dosages[real_name]
            else:
                created_json["dosages"] = {}
            res = Drug(name=real_name, data=created_json)
        elif resource_name == "symptoms":
            res = Symptom(name = real_name, data=created_json)
        
        try:
            db_session.add(res) 
            db_session.commit()
        except IntegrityError:
            db_session = get_session()
            print "Already exists"

if __name__ == "__main__":
    processed_data_folder = os.path.join('..', 'how-to-get-healthy', 'processed_data')
    word_lists_folder = os.path.join('..', 'how-to-get-healthy', 'word_lists')
    data_json_path = os.path.join(processed_data_folder, 'data.json')
    drugs_path = os.path.join(word_lists_folder, 'drugs_stemmed.txt')
    symptom_path = os.path.join(word_lists_folder, 'symptoms_both_ways_stemmed.txt')
    pickled_path = "associations_object"

    if os.path.isfile(pickled_path):
        print "Loading pickled associations"
        f = open(pickled_path)
        a = pickle.load(f)
    else:
        a = Associations(data_json_path, symptom_path, drugs_path)
        a.train()

        # Pickle entire object for future use
        f = open(pickled_path, 'w')
        pickle.dump(a, f)
        
    # Associations
    create_json("symptoms", a.symptom_grandparents, a.symptom_baskets, a.symptom_representatives, a.symptom_postCounts)
    create_json("drugs", a.drug_grandparents, a.drug_baskets, a.drug_representatives, a.drug_postCounts)
    
