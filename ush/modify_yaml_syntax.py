#!/usr/bin/env python3
# open a text file, find the old template, replace the template, write out
import sys
import re
fname = sys.argv[1]

def get_word_in_dollar_parentheses(text):
    pattern = r'\$\((.*?)\)'
    matches = re.findall(pattern, text)
    return matches

with open(fname, 'r') as file:
    filedata = file.readlines()
# do stuff
newdata = []
for line in filedata:
    matches = get_word_in_dollar_parentheses(line)
    if len(matches) > 0:
        print(line)
        for match in matches:
            line = line.replace("$(%s)" % match, "{{ %s }}" % match)
        print(line)
    newdata.append(line)

# write out file
with open(fname, 'w') as file:
    file.writelines(newdata)