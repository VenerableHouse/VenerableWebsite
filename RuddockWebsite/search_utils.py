def parse_keywords(query):
  """
  Parses the string for keywords. Returns a set of keywords, which contains no
  duplicates.
  """
  return set(query.lower().split())

def count_matches(data_keywords, query_keywords, partial_keywords=None):
  """
  Counts the number of matches between the provided data keywords (a parsed
  data point in the data set you're searching through) and the query's
  keywords. Optionally provide a set of keywords that can be partial matches as
  well (a partial match is valued the same as an exact match).

  All inputs should be sets of strings (lists of strings would also work, but
  sets are guaranteed to not contain duplicates and therefore may have more
  accurate results).
  """
  matches = 0
  for data_keyword in data_keywords:
    # Exact matches
    if data_keyword in query_keywords:
      matches += 1
    elif partial_keywords is not None:
      # Check if each partial keyword is a prefix of the current keyword.
      for partial_keyword in partial_keywords:
        if data_keyword[:len(partial_keyword)] == partial_keyword:
          matches += 1
          break
  return matches
