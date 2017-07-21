import json
import io
import os
import editdistance as ed
import re
import time
import associations
    
def is_drug(word, drug_parents, drug_grandparents):
    if word not in drug_parents:
        return None
    if drug_parents[word] in drug_grandparents:
        return drug_parents[word]

def is_dosage(word):
    return re.match("[0-9]+(g|mg)", word)

def preprocess_post(post):
    ret_post = list()

    for idx, word in enumerate(post):
        if word in ["mg", "g"] and idx - 1 >= 0 and post[idx - 1].isdigit():
            
            # This should be e.g 200mg or 6g
            full_dose = post[idx - 1] + word
            ret_post.append(full_dose)
        elif not word.isdigit():
            ret_post.append(word)
            
    return ret_post

def trim(dose):
    if "mg" in dose:
        return dose.split("mg")[0] + "mg"
    if "g" in dose:
        return dose.split("g")[0] + "g"
    return dose

def closest_drug(post, ind, drug_parents, drug_grandparents):
    search_radius = 1
    while ind - search_radius >= 0 or ind + search_radius < len(post):
        
        if ind - search_radius >= 0:
            real_drug = is_drug(post[ind - search_radius], drug_parents, drug_grandparents)
            if real_drug:
                return real_drug
        
        if ind + search_radius < len(post):
            real_drug = is_drug(post[ind + search_radius], drug_parents, drug_grandparents)
            if real_drug:
                return real_drug

        search_radius += 1

class Dosages:

    def __init__(self, data, drug_parents, drug_grandparents, drug_representatives):
        self.data = data
        self.drug_parents = drug_parents
        self.drug_grandparents = drug_grandparents
        self.drug_representatives = drug_representatives

    def train(self):
        # Collects the amount of times a dose has been mentioned for each drug 
        self.drug_dosages = dict()
        mentions = dict()

        progress = 0
        start = time.time()
        print "Finding drug dosages"

        interval = 10000
        for thread in self.data:

            progress += 1
            if progress % interval == 0:
                print "Progressing at", progress, "/", len(self.data)
                print time.time() - start, "seconds taken so far"

            for post in thread:
                post = associations.custom_split_stemmed(post)
                p_post = preprocess_post(post)
                for idx, word in enumerate(p_post):
                    if is_dosage(word):
                        closest_drug_name = closest_drug(p_post, idx, self.drug_parents, self.drug_grandparents)
                        word = trim(word)
                        if not closest_drug_name:
                            continue
                        closest_drug_name = self.drug_representatives[closest_drug_name]
                        
                        if closest_drug_name not in self.drug_dosages:
                            self.drug_dosages[closest_drug_name] = dict()
                        if word not in self.drug_dosages[closest_drug_name]:
                            self.drug_dosages[closest_drug_name][word] = 1
                        else:
                            self.drug_dosages[closest_drug_name][word] += 1
                            
                        # Add to mentions dict
                        # TODO this legit
                        if closest_drug_name not in mentions:
                            mentions[closest_drug_name] = dict()
                        if word not in mentions[closest_drug_name]:
                            mentions[closest_drug_name].setdefault(word, [])
                            mentions[closest_drug_name][word].append(p_post)

        print "Dosages done."
        return self.drug_dosages
if __name__ == "__main__":
    pass

