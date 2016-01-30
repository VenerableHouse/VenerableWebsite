def parse_keywords(query):
  """
  Parses the string for keywords. Returns a set of keywords, which contains no
  duplicates.
  """
  return set(query.lower().split())

def count_matches(data_keywords, query_keywords, partial_keywords=[]):
  """
  Counts the number of matches between the provided data keywords (a parsed
  data point in the data set you're searching through) and the query's
  keywords. Optionally provide a set of keywords that can be partial matches as
  well (a partial match is valued the same as an exact match).

  All inputs should be sets of strings (lists of strings would also work, but
  sets are guaranteed to not contain duplicates and therefore may have more
  accurate results).
  """
  # Partial keywords should be matched starting with the longest partials
  # (least ambiguous) to the shortest partials (most ambiguous). Once a partial
  # is used to match a word, it should not be used again.
  partial_keyword_list = sorted(list(partial_keywords), key=len, reverse=True)
  used_partial_keywords = set()

  matches = 0
  for data_keyword in data_keywords:
    # Exact matches
    if data_keyword in query_keywords:
      matches += 1
    else:
      # Check if each partial keyword is a prefix of the current keyword.
      for partial_keyword in partial_keyword_list:
        if partial_keyword in used_partial_keywords:
          continue
        if data_keyword[:len(partial_keyword)] == partial_keyword:
          matches += 1
          used_partial_keywords.add(partial_keyword)
          break
  return matches
