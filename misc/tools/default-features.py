"""
Turns OpenType features on by default in a compiled font.

The lookups of the given features are added to "ccmp", a feature that
every shaping engine applies to all text and that can't be turned off.
Lookups run in lookup-list order no matter which feature lists them, so
text shapes exactly as if the features were turned on by hand.

The features keep their own tags, so turning one on is still valid.
Turning one off no longer has any effect.

Usage:

  python misc/tools/default-features.py cv05,ss07 build/fonts/var/InterVariable.ttf

"""
import sys, argparse
from fontTools.ttLib import TTFont

# feature which lists the lookups of the default features
CARRIER = "ccmp"


def die(msg):
  print("default-features: " + msg, file=sys.stderr)
  sys.exit(1)


# feature_lookups returns the lookup indices of feature tag
def feature_lookups(gsub, tag):
  lookups = set(
    tuple(r.Feature.LookupListIndex)
    for r in gsub.FeatureList.FeatureRecord if r.FeatureTag == tag)
  if len(lookups) == 0:
    die("font has no feature '%s'" % tag)
  if len(lookups) > 1:
    die("feature '%s' differs between languages (not supported)" % tag)
  return lookups.pop()


# check_carrier makes sure that every script and language applies CARRIER
def check_carrier(gsub):
  records = gsub.FeatureList.FeatureRecord
  for script in gsub.ScriptList.ScriptRecord:
    langs = [(r.LangSysTag, r.LangSys) for r in script.Script.LangSysRecord]
    if script.Script.DefaultLangSys:
      langs.append(("dflt", script.Script.DefaultLangSys))
    for langtag, lang in langs:
      if CARRIER not in [records[i].FeatureTag for i in lang.FeatureIndex]:
        die("%s/%s has no '%s' feature" % (
          script.ScriptTag, langtag.strip(), CARRIER))


def set_default_features(ttfont, tags):
  gsub = ttfont["GSUB"].table
  if getattr(gsub, "FeatureVariations", None):
    die("GSUB has feature variations (not supported)")
  if "GPOS" in ttfont:
    gpos_tags = [r.FeatureTag for r in ttfont["GPOS"].table.FeatureList.FeatureRecord]
    for tag in tags:
      if tag in gpos_tags:
        die("feature '%s' also positions glyphs (not supported)" % tag)
  check_carrier(gsub)

  lookups = set()
  for tag in tags:
    lookups.update(feature_lookups(gsub, tag))

  for r in gsub.FeatureList.FeatureRecord:
    if r.FeatureTag == CARRIER:
      r.Feature.LookupListIndex = sorted(lookups.union(r.Feature.LookupListIndex))
      r.Feature.LookupCount = len(r.Feature.LookupListIndex)


def main():
  argparser = argparse.ArgumentParser(
    description='Turn OpenType features on by default')
  a = lambda *args, **kwargs: argparser.add_argument(*args, **kwargs)
  a('-o', '--output', metavar='<file>',
    help='Output font file. Defaults to input file (overwrite)')
  a('features', metavar='<tags>',
    help='Comma-separated feature tags, e.g. "cv05,ss07"')
  a('input', metavar='<file>', help='Input font file')

  args = argparser.parse_args()

  tags = [tag for tag in args.features.split(',') if tag]
  if CARRIER in tags:
    die("'%s' is already on by default" % CARRIER)

  ttfont = TTFont(args.input, recalcBBoxes=False, recalcTimestamp=False)
  if "GSUB" not in ttfont:
    die("font has no GSUB table")
  set_default_features(ttfont, tags)

  outfile = args.output or args.input
  ttfont.save(outfile)


if __name__ == '__main__':
  main()
