#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Connvertisseur Moodle XML --> XML Opale ScenariChain"""

import xml.etree.ElementTree as ET
import re
import os

from random import shuffle


import HTMLParser
h = HTMLParser.HTMLParser()


def cleanhtml(raw_html):
    raw_html = h.unescape(raw_html)
    raw_html = raw_html.replace("&nbsp;", u" ")
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


def convert_Moodle_XML_to_quiz(params):
        u"""Conversion d'exercices Moodle (quiz)."""
        # See "https://docs.moodle.org/3x/fr/Format_XML_Moodle"
        # params must be : {"file":import_file, "model_filter": "["cloze", "multichoice", "matching"]"}

        # print("----- convert_Moodle_XML_to_quiz -----")

        import_file = open(params["file"], "r")

        # On s'assure que le curseur de lecture est au début du fichier.
        import_file.seek(0)

        tree = ET.parse(import_file)
        root = tree.getroot()
        # groupe_title = h.unescape(root.find('./data/title').text).encode("utf-8")

        questions_list = []

        if not root.tag == "quiz":
            message = u"Votre fichier n'est pas dans un format XML Moodle valide. Assurez-vous de sélectionner un fichier « .xml », généré depuis des Quiz Moodle V? ou plus."
            print(message)
            return questions_list

        nb_exos = 0
        current_folder = "results"

        # Liste d'exercice non reconnus (qui ne seront pas importés)
        unrecognized_list = {}

        # last_question = len(root)

        if params["model_filter"] == "all":
            # params["model_filter"] = ["cloze", "multichoice", "matching"]
            params["model_filter"] = ["cloze"]

        for qnum, question in enumerate(root):
            param_export = None
            question_type = question.get('type')

            if question_type == "category":
                cat_structure = question.find('category').find('text').text.strip()
                cat_structure = cat_structure.replace(" ", "_").replace(".", "_")
                # On s'assure que les accents sont bien en unicode.

                # sur Moodle, la categorie "$course$" est un mot réservé qui fait référence au cours courant.
                cat_structure = cat_structure.replace("../", "").replace("$course$/", "")
                cat_structure = cat_structure.encode("utf-8")
                # cat_structure = cat_structure.split('/')
                current_folder = "results/%s" % cat_structure
                if not os.path.exists(current_folder):
                    os.makedirs(current_folder)

            # Si le type de question fait partie des modeles à importer
            elif question_type in params["model_filter"]:
                # TODO : ici il faudrait s'assurer que le titre ne dépasse pas X chars ?
                question_dict = {"title": question.find('name').find('text').text.strip()}

                if question_type == "cloze":
                    # Plus d'infos sur ce type ici : https://docs.moodle.org/3x/fr/Question_cloze_%C3%A0_r%C3%A9ponses_int%C3%A9gr%C3%A9es
                    # LOG.info("----- Nouvelle question de type 'cloze' (%s) -----" % question_dict["title"])
                    # modele_export = "texteatrous"
                    template_file = "templates/Opale36/TaT.quiz"
                    donnees = question.find('questiontext').find('text').text
                    donnees = cleanhtml(donnees)
                    feedbacks = {"good_reps": [], "bad_reps": []}
                    # Il faut maintenant parser les donnees à la recherches de codes du style :
                    # {1:MULTICHOICE:BAD_REP1#fdbk1~%100%GOOD_REP1#fdbk2~BAD_REP2#fdbk3~BAD_REP3#fdbk4}

                    pattern_trous = r"{(.+?)}"
                    pattern_percent = re.compile(r"%([0-9]*?)%")
                    matches = re.finditer(pattern_trous, donnees)
                    for match in matches:
                        trou = match.group(1)
                        good_reps = []
                        bad_reps = []
                        parsed_trou = trou.split(":", 3)
                        # nb_points = parsed_trou[0]
                        type_trou = parsed_trou[1]
                        trou = parsed_trou[2].split("~")
                        if "MULTICHOICE" in type_trou or "MC" in type_trou:
                            # exemple : {1:MC:Mauvaise rép.#Rétroaction pour cette rép.~Autre mauvaise rép.#Rétroaction pour cette autre mauvaise réponse~=Bonne rép.#Rétroaction pour la bonne rép.~%50%Réponse partiellement juste#Rétroaction pour cette rép.}
                            for rep in trou:
                                rep_group = "bad"
                                fraction = pattern_percent.search(rep)
                                if fraction is not None:
                                    fraction = fraction.group(1)
                                    if fraction != "100":
                                        print("----- ATTENTION : cloze with fraction != 100 !! (%s) -----" % fraction)
                                    rep = pattern_percent.sub('', rep)
                                    rep_group = "good"
                                elif rep.startswith("="):
                                    # on retire le "=" indiquant la bonne réponse
                                    rep = rep[1:]
                                    rep_group = "good"

                                # On sépare la réponse de son feedback
                                rep = rep.split("#")
                                if rep_group == "bad":
                                    # LOG.info("----- Mauvaise -----(%s)" % rep)
                                    if len(rep) > 1:
                                        feedbacks["bad_reps"].append(rep[1])
                                    bad_reps.append(rep[0])
                                else:
                                    if len(rep) > 1:
                                        feedbacks["good_reps"].append(rep[1])
                                    good_reps.append(rep[0])

                            # [TODO] ICI Si plus d'un élément dans good reps, traiter les synonymes
                            good_rep = "[SYNONYME ?]".join(good_reps)
                            if len(good_reps) > 1:
                                # On utilise les accolades aléatoires (une des bonnes réponses sera piochée au hasard)
                                good_rep = "{%s}" % (good_rep)

                            # syntaxe Opale pour multichoix :
                            #   <op:gapM><sp:options><sp:option>BONchoix</sp:option><sp:option>MAUVAISchoix1</sp:option></sp:options></op:gapM>BONchoix
                            options = good_reps + bad_reps
                            shuffle(options)
                            trou = "<op:gapM><sp:options>"
                            for reponse in options :
                                trou = "%s<sp:option>%s</sp:option>" % (trou, reponse)
                            # transforme la liste "options" en chaine de caractères :
                            trou = "%s</sp:options></op:gapM>%s" % (trou, good_rep)

                        elif "SHORTANSWER" in type_trou or "SA" in type_trou:
                            # exemple : {1:SHORTANSWER:=réponse attendue#bonne réponse~*#rétroaction pour toute autre réponse}
                            for rep in trou:
                                rep = rep.split("#")
                                if rep[0].startswith("="):
                                    # on retire le "=" indiquant la seule bonne réponse
                                    trou = rep[0][1:]
                                    if len(rep) > 1:
                                        feedbacks["good_reps"].append(rep[1])
                                elif len(rep) > 1:
                                        feedbacks["bad_reps"].append(rep[1])

                        else:
                            print("----- ATTENTION : cloze with unrecognized TYPE!! (%s) -----" % trou)
                            message = u"----- ATTENTION : cloze with unrecognized TYPE! (%s) -----" % trou
                            print(message)
                        donnees = donnees.replace(match.group(), "<sc:textLeaf role='gap'>%s</sc:textLeaf>" % trou)

                    for feedback_type in ['generalfeedback', 'correctfeedback', 'incorrectfeedback', 'partiallycorrectfeedback']:
                        match = question.find(feedback_type)
                        if match is not None:
                            # ici tester si match.format = 'html' ?
                            # moodle formats : html (default), moodle_auto_format, plain_text et markdown
                            feedbacks[feedback_type] = match.find('text').text
                            if feedbacks[feedback_type] is None:
                                feedbacks[feedback_type] = ""
                            else:
                                feedbacks[feedback_type] = cleanhtml(feedbacks[feedback_type])
                        else:
                            feedbacks[feedback_type] = ""

                    # Todo : partiallycorrectfeedback

                    """
                    # shuffleanswers indique si l'ordre des propositions est aléatoire
                    # pas utilisé dans Opale ?
                    shuffleanswers = question.find('shuffleanswers')
                    if shuffleanswers is not None:
                        # attention : <shuffleanswers> est parfois noté 0/1, et parfois true/false
                        list_order = int(shuffleanswers.text) + 1
                    else:
                        list_order = 1
                    """
                    feedback_bon = feedbacks['correctfeedback']
                    if len(feedbacks["good_reps"]) > 0:
                        feedback_bon = "%s<div>indications spécifiques:%s</div>" % (feedback_bon, "<br/>".join(feedbacks["good_reps"]))
                    feedback_mauvais = feedbacks['incorrectfeedback']
                    if len(feedbacks["bad_reps"]) > 0:
                        feedback_mauvais = "%s<div>indications spécifiques:%s</div>" % (feedback_mauvais, "<br/>".join(feedbacks["bad_reps"]))
                    # concatenation tous les feedback en un seul :
                    explication = ''
                    for feedback_type in ['generalfeedback', 'correctfeedback', 'incorrectfeedback', 'partiallycorrectfeedback']:
                        if feedbacks[feedback_type]:
                            explication = "%s<sp:txt><op:txt><sc:para xml:space='preserve'>%s</sc:para></op:txt></sp:txt>" % (explication, feedbacks[feedback_type])
                    param_export = {"title"      : question_dict["title"].encode("utf-8"),
                                    "donnees"    : donnees.encode("utf-8"),
                                    "explication": explication.encode("utf-8")
                                    }
                    nb_exos += 1

                elif question_type == "multichoice":
                    # TODO : preliminary DRAFT only
                    print("----- Nouvelle question de type 'multichoice' -----")

                    template_file = "templates/Opale36/QCM.quiz"
                    question_dict = {"good_rep": [],
                                     "bad_rep":  []}
                    for answer in question.find('answers'):
                        answer_text = answer.find('text').text
                        if answer_text:
                            answer_text = answer_text.replace("&#x2019;", "'")
                            if int(answer.find("correct").text):
                                question_dict["good_rep"].append(h.unescape(answer_text).encode("utf-8"))
                            else:
                                question_dict["bad_rep"].append(h.unescape(answer_text).encode("utf-8"))

                    enonce = question.find('questiontext').find('text').text
                    # test the questiontext format ? html ?

                    # if "#x2019;" in enonce:
                    #    print enonce
                    enonce = enonce.replace("&#x2019;", "'")

                    param_export = {"title":            question_dict["title"],
                                    "enonce":           h.unescape(enonce).encode("utf-8"),
                                    "bonnesrep":        "\n".join(question_dict["good_rep"]),
                                    "mauvaisesrep":     "\n".join(question_dict["bad_rep"]),
                                    "tot":              "5",
                                    "givetrue":         "2",
                                    "minfalse":         "0",
                                    "options":          ["checkbox", "split"],
                                    "feedback_general": "",
                                    "feedback_bon":     "",
                                    "feedback_mauvais": ""
                                    }
                    nb_exos += 1

                elif question_type == "matching":
                    # TODO : preliminary DRAFT only
                    print("----- Nouvelle question de type 'matching' -----")
                    template_file = "templates/Opale36/categorisation.quiz"
                else:
                    # other Moodle question types : truefalse|shortanswer|matching|essay|numerical|description
                    if question_type not in unrecognized_list :
                        unrecognized_list[question_type] = 1
                    else:
                        unrecognized_list[question_type] = unrecognized_list[question_type] + 1

                if param_export is not None:
                    # Read in the file
                    with open(template_file, 'r') as file :
                        filedata = file.read()
                    for param in param_export:
                        # Replace the target string
                        filedata = filedata.replace('$$%s$$' % param, param_export[param])

                    # Write the file out again
                    with open("%s/%s.quiz" % (current_folder, nb_exos), 'w') as file:
                        file.write(filedata)

        if nb_exos == 0:
            message = u"Aucun exercice compatible détecté dans votre fichier."
            print(message)

        if len(unrecognized_list.keys()) > 0:
            message = u"Attention : Certaines questions utilisaient un modèle non reconnu et n'ont pas été importées. (%s)" % unrecognized_list
            print(message)

        return questions_list


convert_Moodle_XML_to_quiz({
    "file": "export_moodle.xml",
    "model_filter": "all"}
)
