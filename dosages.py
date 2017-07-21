import json
import io
import os
import editdistance as ed
import re
import time
import associations
from models import Post, Drug, bridge_dosage_quotes
from progress_indicator import Progress_indicator


def is_drug(word, drug_parents, drug_grandparents):
    if word not in drug_parents:
        # This is possible because we have preprocessed expressions like "16 mg" into "16mg"
        return None
    if drug_parents[word] in drug_grandparents:
        return drug_parents[word]

def is_dosage(word):
    return re.match("[0-9]+(g|mg)", word)

def preprocess_post(post):
    # Returns a post where dosages are cleaned into nicer form.
    ret_post = list()

    for idx, word in enumerate(post):

        # Deal with expressions including a space, eg. "1 g", "400 mgx3"
        if idx - 1 >= 0 and post[idx - 1].isdigit():
            multiplier = 1
            if word.startswith("g"):
                multiplier = 1000
                word = "mg"
            if word.startswith("mg"):
                value = multiplier * int(post[idx - 1]) # possible conversion from g to mg
                full_dose = str(value) + "mg" # forget anything after mg, eg. mgx3->mg
                del ret_post[-1] # remove previously added element, eg. "400" if we are now adding "400mg"
                ret_post.append(full_dose)
                continue

        # Deal with expressions without a space, eg. "1g", "400mgx3"
        if re.match("[0-9]+(g)", word):
            value = 1000 * int(word.split("g")[0])
            word = str(value) + "mg"
        if re.match("[0-9]+(mg)", word):
            ret_post.append(word.split("mg")[0] + "mg") # forget anything after mg
        else:
            # Not a dosage (or possibly "400" of "400 mg"; in that case this addition will be removed in next iteration)
            ret_post.append(word)
            
    return ret_post

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

    def __init__(self, drug_parents, drug_grandparents, drug_representatives):
        self.drug_parents = drug_parents
        self.drug_grandparents = drug_grandparents
        self.drug_representatives = drug_representatives

    def train(self, db):
        # Collects the amount of times a dose has been mentioned for each drug 
        self.drug_dosages = dict()

        print "Finding drug dosages"

        # Collect drug id's for fast referencing
        drug_ids = {}
        for drug in db.query(Drug):
            drug_ids[drug.name] = drug.id

        progress_indicator = Progress_indicator(db.query(Post).count())
        for post in db.query(Post):
            progress_indicator.tick()

            post_id = post.id
            post = associations.custom_split(post.lemmatized)
            p_post = preprocess_post(post)

            for idx, word in enumerate(p_post):
                if is_dosage(word):
                    closest_drug_name = closest_drug(p_post, idx, self.drug_parents, self.drug_grandparents)
                    dosage = word
                    if not closest_drug_name:
                        continue
                    closest_drug_name = self.drug_representatives[closest_drug_name]

                    if closest_drug_name not in self.drug_dosages:
                        self.drug_dosages[closest_drug_name] = dict()
                    if dosage not in self.drug_dosages[closest_drug_name]:
                        self.drug_dosages[closest_drug_name][dosage] = 1
                    else:
                        self.drug_dosages[closest_drug_name][dosage] += 1

                    drug_id = drug_ids[closest_drug_name]
                    dosage_value = int(dosage.split("mg")[0])
                    if dosage_value > 4000:
                        print 'Huge dosage value from', word
                    link = bridge_dosage_quotes(post_id=post_id, drug_id=drug_id, dosage=dosage_value)
                    db.add(link)
                    db.commit()

        print "Dosages done."
        raise
        return self.drug_dosages
if __name__ == "__main__":
    pass

