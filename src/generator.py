#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import argparse
import sys
import os
import datetime
import pytz
import json
import logzero
import gettext
import yaml
from gettext import gettext as _
from logzero import logger as log
from stdnum import isbn, issn
from jinja2 import Environment, FileSystemLoader
from locale import strxfrm
from babel.support import Translations
from babel.core import parse_locale

def formatIdentifier(stringToFormat, type):
    """
        This is used to format/check ISBN and ISSN numbers
    """
    if type.lower() == "isbn":
        if isbn.is_valid(stringToFormat):
            log.debug("OK ISBN: {0}".format(stringToFormat))
            return isbn.format(stringToFormat)
        else:
            log.warning("Malformed ISBN: {0}".format(stringToFormat))
            return stringToFormat

    elif type.lower() == "issn":
        if issn.is_valid(stringToFormat):
            log.debug("OK ISSN: {0}".format(stringToFormat))
            return issn.format(stringToFormat)
        else:
            log.warning("Malformed ISSN: {0}".format(stringToFormat))
            return stringToFormat

def generateLogoUrl(locationForLogoCheck):
    """
        Checks if the location has a logo, and if so returns the location of the file, otherwise returns a default logo
    """
    tmp = locationForLogoCheck.replace(" ", "")

    if os.path.isfile("static/img/locations/{0}.png".format(tmp)):
        return "img/locations/{0}.png".format(tmp)
    else:
        log.warning("No Logo for {0}!".format(locationForLogoCheck))
        return "img/locations/nologo.png"

def prepareSearchJson(d):
    """
        recursively remove empty lists, empty dicts, or None elements from a dictionary
        adapted from https://gist.github.com/nlohmann/c899442d8126917946580e7f84bf7ee7
    """

    def empty(x):
        return x is None or x == {} or x == [] or x == ""

    if not isinstance(d, (dict, list)):
        return d
    elif isinstance(d, list):
        return [v for v in (prepareSearchJson(v) for v in d) if not empty(v)]
    else:
        return {k: v for k, v in ((k, prepareSearchJson(v)) for k, v in d.items()) if not empty(v)}

def writePage(page, locale, language, fileNamePrefix):
    log.info("Reading Page Template: {0}".format(page))
    targetFilename = "{0}{1}".format(fileNamePrefix, os.path.splitext(page)[0])
    log.info("Writing Page: {0}".format(targetFilename))

    templateVars = {
        "locale": locale,
        "language": language,
        "fileNamePrefix": fileNamePrefix,
        "targetFilenameWithoutPrefix": os.path.splitext(page)[0]
    }

    template = jinja2Env.get_template(page)
    with open("{0}/upload/{1}".format(workDir, targetFilename), "w") as templateWriter:
        templateWriter.write(template.render({**sharedTemplateVars, **templateVars}))

def writeLocation(location, locale, language, fileNamePrefix):
    log.info("Writing location: {0}".format(location))
    targetFilenameWithoutPrefix = "location_{0}.html".format(location.replace(" ", ""))
    destFile = "upload/{0}{1}".format(fileNamePrefix, targetFilenameWithoutPrefix)

    templateVars = {
        "location": location,
        "categories": locationsAndCategories[location],
        "locale": locale,
        "language": language,
        "fileNamePrefix": fileNamePrefix,
        "targetFilenameWithoutPrefix": targetFilenameWithoutPrefix
    }

    with open("{0}/{1}".format(workDir, destFile), "w") as locationWriter:
        locationWriter.write(locationTemplate.render({**sharedTemplateVars, **templateVars}))

#### Config ####
# CLI Params
parser = argparse.ArgumentParser("generator.py")
parser.add_argument("--loglevel", help="DEBUG, INFO, ERROR, CRITICAL. Default INFO")
parser.add_argument("--jsonlog", help="Log output as JSON. Default no")
parser.add_argument("--source", help="Path to inventory.csv. Default ~/library-media-inventory/inventory.csv")
args = vars(parser.parse_args())

# Logging
loglevelFromCli = getattr(sys.modules["logging"], args["loglevel"].upper() if args["loglevel"] else "INFO")
jsonLogFromCli = args["jsonlog"].upper() if args["jsonlog"] else "N"
logzero.loglevel(loglevelFromCli)

# Do we want to log as json?
if (jsonLogFromCli == "Y" or jsonLogFromCli == "YES"):
    logzero.json()

log.debug("Command Line Parameters: {0}".format(args))

# Load config
configFile = "config.yml"
try:
    with open(configFile, "r") as configString:
        config = yaml.load(configString, Loader=yaml.FullLoader)

except FileNotFoundError:
    log.critical("Can't read {0}!".format(configFile))
    exit(1)

log.info("Library Name: {0}".format(config["libraryName"]))
log.info("Locales to generate: {0}".format(config["languages"]))
log.info("Default locale: {0}".format(config["defaultLanguage"]))
log.info("Timezone: {0}".format(config["timezone"]))

# Defaults
sourceFile = args["source"] if args["source"] else "~/library-media-inventory/inventory.csv"
log.info("Source file: {0}".format(sourceFile))

## Some variables, init jinja2
# Current folder
workDir = os.path.dirname(os.path.realpath(__file__))
log.info("Working Directory: {0}".format(workDir))

jinja2Env = Environment(
    loader=FileSystemLoader("templates"),
    extensions=["jinja2.ext.i18n"],
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True
)
locationTemplate = jinja2Env.get_template("_location_boilerplate.html.j2")

# Generation Time
generationTime = datetime.datetime.now().astimezone(pytz.timezone(config["timezone"])).replace(microsecond=0).isoformat()
log.info("Generation Time: {0}".format(generationTime))

#### End config ####

# Read the csv and sort it
try:
    with open(sourceFile, newline="") as csvFileReader:
        readFile = csv.DictReader(csvFileReader)
        media = sorted(readFile, key = lambda tup: (
            strxfrm(tup["location"].lower()), # Sorting is: Location (branch office) -> Category -> Name
            strxfrm(tup["category"].lower()),
            strxfrm(tup["name"].lower()))
        )

except FileNotFoundError:
    log.critical("Can't read library.csv!")
    exit(1)

log.debug("Media: {0}".format(media))

# Here we build a nested dictionary in the form
# -> location 1
#   -> category 1
#   -> category 2
# -> location 2
#   -> category 1
#   -> category 2
# ...
locationsAndCategories = {}
for record in media: # Loop through all records
    if not record["location"] in locationsAndCategories: # ... if we don't have the location (branch office)
        locationsAndCategories[record["location"]] = {} # ... add it do the dict

    if not record["category"] in locationsAndCategories[record["location"]]: # now we do the same with the categories
        locationsAndCategories[record["location"]][record["category"]] = {}

log.debug("Locations and Categories: {0}".format(locationsAndCategories))

# We also need a list of all categories
allCategories = {}
for record in media: # Loop through all records
    if not record["category"] in allCategories: # ... if we don't have the location (branch office)
        allCategories[record["category"]] = {} # ... add it do the dict

allCategories = sorted(allCategories)

log.debug("Categories: {0}".format(allCategories))

# Reverse Locations as a quick fix for issue #1
reversedLocations = sorted(locationsAndCategories, reverse=True)

# Shared Template vars
sharedTemplateVars = {
    "locations": reversedLocations,
    "logoUrl": generateLogoUrl,
    "generationTime": generationTime,
    "locationsAndCategories": locationsAndCategories,
    "libraryName": config["libraryName"],
    "locales": config["languages"],
    "defaultLocale": config["defaultLanguage"],
    "allCategories": allCategories,
    "media": media,
    "formatIdentifier": formatIdentifier
}
log.debug("sharedTemplateVars: {0}".format(sharedTemplateVars))

# We need to write a version of every page for every locale
for locale in config["languages"]:
    log.info("Generating pages for locale: {0}".format(locale))
    language = parse_locale(locale)[0]
    log.debug("Parsed language {0} from locale {1}".format(language, locale))

    if (locale == config["defaultLanguage"]):
        fileNamePrefix = ""
    else:
        fileNamePrefix = locale

    # Initialise the locale
    translation = Translations.load("locale", [locale])
    jinja2Env.install_gettext_translations(translation)

    # Write the pages
    for page in [x for x in os.listdir(workDir + "/templates") if (os.path.splitext(x)[1] == ".j2" and x[0] != "_")]:
        writePage(page, locale, language, fileNamePrefix)

    # Write the locations
    for location in reversedLocations:
        writeLocation(location, locale, language, fileNamePrefix)

# Write media json
with open("upload/media_search.json", "w") as mediaJsonWriter:
    log.info("Writing Media Information for the search as JSON...")
    json.dump(prepareSearchJson(media), mediaJsonWriter)
