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
    cleantext = raw_html
    if raw_html is not None:
        raw_html = h.unescape(raw_html)
        raw_html = raw_html.replace("&nbsp;", u" ")
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', raw_html)
        cleantext = cleantext.strip().replace("\t", " ").replace("  ", " ").replace("\r", "\n").replace("\n\n", "\n")
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
            params["model_filter"] = ["cloze", "multichoice", "truefalse", "gapselect", "shortanswer", "ddwtos"]

        for qnum, question in enumerate(root):
            param_export = None
            question_type = question.get('type')

            if question_type == "category":
                cat_structure = question.find('category').find('text').text.strip()
                # sur Moodle, la categorie "$course$" est un mot réservé qui fait référence au cours courant.
                cat_structure = cat_structure.replace("../", "").replace("$course$/", "")
                for caractere in ["$", "+", "\\", ">", "<", "|", "?", ":", "*", "#", "\"", "~", " ", "."]:
                    cat_structure = cat_structure.replace(caractere, "_")

                # On s'assure que les accents sont bien en unicode.
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
                    template_file = "templates/Opale36/TaT2.quiz"
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
                        good_rep = ['']
                        bad_reps = []
                        placesynonymes = ''
                        synonymes = []
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
                                    if good_rep[0] != '':
                                        synonymes.append(rep[0])
                                    else:
                                        good_rep = [rep[0]]
                            # syntaxe Opale pour multichoix :
                            #   <op:gapM><sp:options><sp:option>BONchoix</sp:option><sp:option>MAUVAISchoix1</sp:option></sp:options></op:gapM>BONchoix
                            options = good_rep + bad_reps + synonymes
                            shuffle(options)
                            trou = "<sp:options>"
                            for reponse in options:
                                trou = "%s<sp:option>%s</sp:option>" % (trou, reponse)
                            trou = "%s</sp:options>" % (trou)
                            if len(synonymes) > 0:
                                placesynonymes = "<sp:synonyms>"
                                for synonyme in synonymes:
                                    placesynonymes = "%s<sp:synonym>%s</sp:synonym>" % (placesynonymes, synonyme)
                                placesynonymes = "%s</sp:synonyms>" % (placesynonymes)
                            else:
                                placesynonymes = ''
                            donnees = donnees.replace(match.group(), "<sc:textLeaf role='gap'><op:gapM>%s%s</op:gapM>%s</sc:textLeaf>" % (placesynonymes, trou, good_rep[0]))

                        elif "SHORTANSWER" in type_trou or "SA" in type_trou:
                            # exemple : {1:SHORTANSWER:=réponse attendue#bonne réponse~*#rétroaction pour toute autre réponse}
                            for rep in trou:
                                rep = rep.split("#")
                                if rep[0].startswith("="):
                                    # on retire le "=" indiquant la seule bonne réponse
                                    trou = rep[0][1:]
                                    good_rep.append(rep[0][1:])
                                    if len(rep) > 1:
                                        feedbacks["good_reps"].append(rep[1])
                                elif len(rep) > 1:
                                        feedbacks["bad_reps"].append(rep[1])
                            donnees = donnees.replace(match.group(), "<sc:textLeaf role='gap'>%s</sc:textLeaf>" % (trou))

                        else:
                            print("----- ATTENTION : cloze with unrecognized TYPE!! (%s) -----" % trou)
                            message = u"----- ATTENTION : cloze with unrecognized TYPE! (%s) -----" % trou
                            print(message)
                            print (good_rep[0])

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
                    #
                    feedback_bon = feedbacks['correctfeedback']
                    if len(feedbacks["good_reps"]) > 0:
                        feedback_bon = u"%s<div>indications spécifiques:%s</div>" % (feedback_bon, "<br/>".join(feedbacks["good_reps"]))
                    feedback_mauvais = feedbacks['incorrectfeedback']
                    if len(feedbacks["bad_reps"]) > 0:
                        feedback_mauvais = u"%s<div>indications spécifiques:%s</div>" % (feedback_mauvais, "<br/>".join(feedbacks["bad_reps"]))
                    """
                    #
                    # concatenation tous les feedback en un seul :
                    explication = ''
                    for feedback_type in ['generalfeedback', 'correctfeedback', 'incorrectfeedback', 'partiallycorrectfeedback']:
                        if feedbacks[feedback_type]:
                            explication = "%s<sp:txt><op:txt><sc:para xml:space='preserve'>%s</sc:para></op:txt></sp:txt>" % (explication, feedbacks[feedback_type])
                    if explication != '':
                        explication = "<sc:globalExplanation><op:res>%s</op:res></sc:globalExplanation>" % (explication)
                    param_export = {"title"      : question_dict["title"].encode("utf-8"),
                                    "donnees"    : donnees.encode("utf-8"),
                                    "explication": explication.encode("utf-8")
                                    }
                    nb_exos += 1

#
#   Question de type "Choix Multiple"
#
                elif question_type == "multichoice":
                    # TODO : preliminary DRAFT only
                    print("----- Nouvelle question de type 'multichoice' -----")
                    # Plus d'infos sur ce type ici : https://docs.moodle.org/3x/fr/Question_%C3%A0_choix_multiples
                    # LOG.info("----- Nouvelle question de type 'choix multiples' (%s) -----" % question_dict["title"])
                    template_file = "templates/Opale36/qcm.quiz"
                    # modele_export = "question à choix multiples"
                    #
                    donnees = question.find('questiontext').find('text').text
                    donnees = cleanhtml(donnees)
                    #
                    feedbacks = {"good_reps": [], "bad_reps": []}
                    #
                    #
                    # rammassage des réponses et de l'indicateur de bonne réponse
                    # puis construction des réponses scenari
                    #
                    listereponses = ''
                    for balise in question :
                        if balise.tag == "answer":
                            #  liste_reponses_possibles.append(balise.find('text').text)
                            fraction = balise.get("fraction")
                            reponse = balise.find('text').text
                            if fraction > "0":
                                check = "checked"
                            else:
                                check = "unchecked"

                            reponse = cleanhtml(reponse)
                            listereponses = u"%s<sc:choice solution='%s'><sc:choiceLabel><op:txt><sc:para xml:space='preserve'>%s\
                                        </sc:para></op:txt></sc:choiceLabel></sc:choice>" % (listereponses, check, reponse)

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

                    # on supprime les feedbacks redondant avec ceux de Scenari :
                    feedbacks['correctfeedback'] = feedbacks['correctfeedback'].replace(u"Votre réponse est correcte.", "")
                    feedbacks['incorrectfeedback'] = feedbacks['incorrectfeedback'].replace(u"Votre réponse est incorrecte.", "")
                    feedbacks['partiallycorrectfeedback'] = feedbacks['partiallycorrectfeedback'].replace(u"Votre réponse est partiellement correcte.", "")

                    explication = ''
                    for feedback_type in ['generalfeedback', 'correctfeedback', 'incorrectfeedback', 'partiallycorrectfeedback']:
                        if feedbacks[feedback_type]:
                            explication = "%s%s" % (explication, feedbacks[feedback_type])
                    if explication != '':
                        explication = "<sc:globalExplanation><op:res><sp:txt><op:txt><sc:para xml:space='preserve'>%s</sc:para></op:txt></sp:txt></op:res></sc:globalExplanation>" % (explication)

                    param_export = {"title"           :      question_dict["title"].encode("utf-8"),
                                    "enonce"          :      (donnees).encode("utf-8"),
                                    "listereponses"   :      (listereponses).encode("utf-8"),
                                    "explication"     :      (explication).encode("utf-8")
                                    }
                    nb_exos += 1
#
#
#   Question de type "categorisation"
#
                elif question_type == "matching":
                    # [TODO] : preliminary DRAFT only
                    # seulement 2 a transferer donc, question non traitée ici sera transférée manuellement
                    print("----- Nouvelle question de type 'matching' [preliminary DRAFT only !!] -----")
                    template_file = "templates/Opale36/categorisation.quiz"
#
#
#   Question de type "glisser-déposer sur le texte"
#
                elif question_type == "ddwtos" :
                    print("----- Nouvelle question de type 'glisser-déposer sur le texte' -----")
                    template_file = "templates/Opale36/TaT2.quiz"
                    # Plus d'infos sur ce type ici : https://docs.moodle.org/3x/fr/Question_glisser-d%C3%A9poser_sur_texte
                    # LOG.info("----- Nouvelle question de type 'glisser déposer' (%s) -----" % question_dict["title"])
                    # modele_export = "texteatrous"
                    donnees = question.find('questiontext').find('text').text
                    donnees = cleanhtml(donnees)
                    feedbacks = {"good_reps": [], "bad_reps": []}

                    pattern_trous = r"\[\[([1-9])\]\]"
                    liste_reponses_possibles = []
                    for balise in question :
                        if balise.tag == "dragbox" :
                            liste_reponses_possibles.append(balise.find('text').text)

                    matches = re.finditer(pattern_trous, donnees)
                    for match in matches:
                        numero_bonne_reponse = match.group(1)
                        good_rep = liste_reponses_possibles[int(numero_bonne_reponse) - 1]
                        trou = "<op:gapM><sp:options>"
                        for reponse in liste_reponses_possibles:
                            trou = "%s<sp:option>%s</sp:option>" % (trou, reponse)
                        # transforme la liste "options" en chaine de caractères :
                        trou = "%s</sp:options></op:gapM>" \
                               "%s" % (trou, good_rep)

                        donnees = donnees.replace(match.group(), "<sc:textLeaf role='gap'>%s</sc:textLeaf>" % trou)

                    for feedback_type in ['generalfeedback', 'correctfeedback', 'incorrectfeedback', 'partiallycorrectfeedback']:
                        tous_les_feedbacks_question = question.find(feedback_type)
                        if tous_les_feedbacks_question is not None:
                            # ici tester si match.format = 'html' ?
                            # moodle formats : html (default), moodle_auto_format, plain_text et markdown
                            feedbacks[feedback_type] = tous_les_feedbacks_question.find('text').text
                            if feedbacks[feedback_type] is None:
                                feedbacks[feedback_type] = ""
                            else:
                                feedbacks[feedback_type] = cleanhtml(feedbacks[feedback_type])
                        else:
                            feedbacks[feedback_type] = ""

                    feedbacks['correctfeedback'] = feedbacks['correctfeedback'].replace(u"Votre réponse est correcte.", "")
                    feedbacks['incorrectfeedback'] = feedbacks['incorrectfeedback'].replace(u"Votre réponse est incorrecte.", "")
                    feedbacks['partiallycorrectfeedback'] = feedbacks['partiallycorrectfeedback'].replace(u"Votre réponse est partiellement correcte.", "")
                    # concatenation tous les feedback en un seul :
                    explication = ''
                    for feedback_type in ['generalfeedback', 'correctfeedback', 'incorrectfeedback', 'partiallycorrectfeedback']:
                        if feedbacks[feedback_type]:
                            explication = "%s<sp:txt><op:txt><sc:para xml:space='preserve'>%s</sc:para></op:txt></sp:txt>" \
                                          % (explication, feedbacks[feedback_type])
                    if explication != '':
                        print (explication)
                        explication = "<sc:globalExplanation><op:res>%s</op:res></sc:globalExplanation>" % (explication)
                    param_export = {"title"      : question_dict["title"].encode("utf-8"),
                                    "donnees"    : donnees.encode("utf-8"),
                                    "explication": explication.encode("utf-8")
                                    }
                    nb_exos += 1

#
#
#   Question de type "selectionner le mot manquant"
#
                elif question_type == "gapselect" :
                    print("----- Nouvelle question de type 'selectionner le mot manquant' -----")
                    template_file = "templates/Opale36/TaT2.quiz"
                    # Plus d'infos sur ce type ici : https://docs.moodle.org/3x/fr/Question_cloze_%C3%A0_r%C3%A9ponses_int%C3%A9gr%C3%A9es
                    # LOG.info("----- Nouvelle question de type 'cloze' (%s) -----" % question_dict["title"])
                    # modele_export = "texteatrous"
                    donnees = question.find('questiontext').find('text').text
                    donnees = cleanhtml(donnees)
                    feedbacks = {"good_reps": [], "bad_reps": []}
                    # Il faut maintenant parser les donnees à la recherches de codes du style :
                    # {1:MULTICHOICE:BAD_REP1#fdbk1~%100%GOOD_REP1#fdbk2~BAD_REP2#fdbk3~BAD_REP3#fdbk4}

                    pattern_trous = r"\[\[([0-9]+)\]\]"
                    liste_groupes_reponses = {}
                    liste_reponses_possibles = []
                    #
                    for balise in question :
                        if balise.tag == "selectoption" :
                            numgroupe = str(balise.find('group').text)
                            choix = (balise.find('text').text)
                            dico_reponse = {"text": choix, "group": numgroupe}
                            liste_reponses_possibles.append(dico_reponse)
                            if numgroupe in liste_groupes_reponses :
                                liste_groupes_reponses[numgroupe].append(choix)
                            else :
                                liste_groupes_reponses[numgroupe] = [choix]

                    matches = re.finditer(pattern_trous, donnees)

                    for match in matches:
                        num_good_rep = (int(match.group(1)) - 1)
                        good_rep_grp = liste_reponses_possibles[num_good_rep]
                        good_rep = good_rep_grp["text"]
                        numgroupe = good_rep_grp["group"]
                        options = liste_groupes_reponses[numgroupe]
                        shuffle(options)

                        # transforme la liste "options" en chaine de caractères :
                        trou = "<op:gapM><sp:options>"
                        for reponse in options:
                            trou = "%s<sp:option>%s</sp:option>" % (trou, reponse)
                        trou = "%s</sp:options></op:gapM>" \
                               "%s" % (trou, good_rep)

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

                    # [TODO] : partiallycorrectfeedback

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
                        feedback_bon = "%s%s" % (feedback_bon, (feedbacks["good_reps"]))
                    feedback_mauvais = feedbacks['incorrectfeedback']
                    if len(feedbacks["bad_reps"]) > 0:
                        feedback_mauvais = "%s%s" % (feedback_mauvais, (feedbacks["bad_reps"]))
                    # On supprime les feedbacks redondant avec ceux de Scenari :
                    feedbacks['correctfeedback'] = feedbacks['correctfeedback'].replace(u"Votre réponse est correcte.", "")
                    feedbacks['incorrectfeedback'] = feedbacks['incorrectfeedback'].replace(u"Votre réponse est incorrecte.", "")
                    feedbacks['partiallycorrectfeedback'] = feedbacks['partiallycorrectfeedback'].replace(u"Votre réponse est partiellement correcte.", "")

                    explication = ''
                    # concatenation des feedbacks
                    for feedback_type in ['generalfeedback', 'correctfeedback', 'incorrectfeedback', 'partiallycorrectfeedback']:
                        if feedbacks[feedback_type]:
                            explication = "%s<sp:txt><op:txt><sc:para xml:space='preserve'>%s</sc:para></op:txt></sp:txt>" % (explication, feedbacks[feedback_type])
                    if explication != '':
                        print (explication)
                        explication = "<sc:globalExplanation><op:res>%s</op:res></sc:globalExplanation>" % (explication)
                    param_export = {"title"      : question_dict["title"].encode("utf-8"),
                                    "donnees"    : donnees.encode("utf-8"),
                                    "explication": explication.encode("utf-8")
                                    }
                    nb_exos += 1

#
#
#   Question de type "réponse courte"
#
                elif question_type == "shortanswer":
                    print("----- Nouvelle question de type 'question à réponse courte' -----")
                    template_file = "templates/Opale36/reponse_courte.quiz"
                    # Plus d'infos sur ce type ici : https://docs.moodle.org/3x/fr/Question_%C3%A0_r%C3%A9ponse_courte
                    # LOG.info("----- Nouvelle question de type 'reponse_courte' (%s) -----" % question_dict["title"])
                    # modele_export = "reponse_courte"
                    donnees = question.find('questiontext').find('text').text
                    donnees = cleanhtml(donnees)
                    feedbacks = {"good_reps": [], "bad_reps": []}
                    explications = {"feedback_bon": "", "feedback_mauvais": "", "feedback_general": ""}
                    explications["feedback_general"] = question.find('generalfeedback').find('text').text
                    explications["feedback_general"] = cleanhtml(explications["feedback_general"])

                    liste_reponses_possibles = []
                    for balise in question :
                        if balise.tag == "answer" :
                            feedback = balise.find("feedback").find("text").text
                            fraction = balise.get("fraction")
                            if fraction == "100" :
                                reponseok = (balise.find('text').text)
                                liste_reponses_possibles.append(balise.find('text').text)
                                if feedback is not None:
                                    feedbacks["good_reps"].append(feedback)
                            else :
                                liste_reponses_possibles.append(balise.find('text').text)
                                if feedback is not None:
                                    feedbacks["bad_reps"].append(feedback)

                    reponses = ""
                    for reponse in liste_reponses_possibles :
                        reponses = "%s<sc:value>%s</sc:value>" % (reponses, reponse)

                    if len(feedbacks["good_reps"]) > 0:
                        explications["feedback_bon"] = u"<div>indications spécifiques:%s</div>" % ("<br/>".join(feedbacks["good_reps"]))
                    if len(feedbacks["bad_reps"]) > 0:
                        explications["feedback_mauvais"] = u"<div>indications spécifiques:%s</div>" % ("<br/>".join(feedbacks["bad_reps"]))
                    # concatene tous les feedback en un seul :
                    explication = ''
                    for feedback_type in ['feedback_general', 'feedback_bon', 'feedback_mauvais']:
                        if explications[feedback_type]:
                            explication = "%s<sp:txt><op:txt><sc:para xml:space='preserve'>%s</sc:para></op:txt></sp:txt>" % (explication, explications[feedback_type])
                    param_export = {"title"      : question_dict["title"].encode("utf-8"),
                                    "donnees"    : donnees.encode("utf-8"),
                                    "explication": explication.encode("utf-8"),
                                    "reponses"   : reponses.encode("utf-8")
                                    }
                    nb_exos += 1

#
#
#   Question de type "Vrai/Faux"
#
                elif question_type == "truefalse" :
                    print("----- Nouvelle question de type 'question Vrai/Faux' -----")
                    template_file = "templates/Opale36/qcu.quiz"
                    # Plus d'infos sur ce type ici : https://docs.moodle.org/3x/fr/Question_vrai_ou_faux
                    # LOG.info("----- Nouvelle question de type 'truefalse' (%s) -----" % question_dict["title"])
                    # modele_export = "reponse_courte"
                    donnees = question.find('questiontext').find('text').text
                    donnees = cleanhtml(donnees)
                    feedbacks = {"good_reps": [], "bad_reps": []}
                    explications = {"feedback_bon": "", "feedback_mauvais": "", "feedback_general": ""}
                    explications["feedback_general"] = ''
                    if question.find('generalfeedback').find('text').text:
                        explications["feedback_general"] = question.find('generalfeedback').find('text').text
                        explications["feedback_general"] = cleanhtml(explications["feedback_general"])

                    liste_reponses_possibles = []
                    for balise in question :
                        if balise.tag == "answer" :
                            feedback = balise.find("feedback").find("text").text
                            fraction = balise.get("fraction")
                            if fraction == "100" :
                                reponseok = (balise.find('text').text)
                                liste_reponses_possibles.append(balise.find('text').text)
                                numbonnereponse = (liste_reponses_possibles.index(reponseok) + 1)
                                if feedback is not None:
                                    feedbacks["good_reps"].append(feedback)
                            else :
                                liste_reponses_possibles.append(balise.find('text').text)
                                if feedback is not None:
                                    feedbacks["bad_reps"].append(feedback)

                    choix = ""
                    for reponse in liste_reponses_possibles :
                        choix = "%s<sc:choice><sc:choiceLabel><op:txt><sc:para xml:space='preserve'>%s</sc:para></op:txt></sc:choiceLabel></sc:choice>" \
                                % (choix, reponse)

                    if len(feedbacks["good_reps"]) > 0:
                        explications["feedback_bon"] = (feedbacks["good_reps"])

                    if len(feedbacks["bad_reps"]) > 0:
                        explications["feedback_mauvais"] = (feedbacks["bad_reps"])

                    # concatene tous les feedback en un seul :
                    if len(explications) > 0:
                        explication = "<sp:txt><op:txt><sc:para xml:space='preserve'>"
                        totalexplication = ''
                        for feedback_type in ['feedback_general', 'feedback_bon', 'feedback_mauvais']:
                            totalexplication = "%s%s" % (totalexplication, explications[feedback_type])
                        explication = "%s%s</sc:para></op:txt></sp:txt>" % (explication, totalexplication)

                    param_export = {"title"              : question_dict["title"].encode("utf-8"),
                                    "donnees"            : donnees.encode("utf-8"),
                                    "explication"        : explication.encode("utf-8"),
                                    "choix"              : choix.encode("utf-8"),
                                    "numbonnereponse"    : str(numbonnereponse)
                                    }
                    nb_exos += 1

#
#
#   Autres modèles
#
                else:
                    # other Moodle question types : matching|essay|numerical|description
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
        else :
            print "nombre d'exercices : %s" % nb_exos

        if len(unrecognized_list.keys()) > 0:
            message = u"Attention : Certaines questions utilisaient un modèle non reconnu et n'ont pas été importées. (%s)" % unrecognized_list
            print(message)

        return questions_list


convert_Moodle_XML_to_quiz({
    "file": "export_moodle.xml",
    "model_filter": "all"}
)
