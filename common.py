
def gallonsToCO2Pounds(gallons):
  return gallons*21.5

def poundsToKg(pounds):
  return pounds * 0.453592

class NoSuchFlightError(BaseException):
  def __init__(self, flight):
    self.flight = flight

def findMinDistStr(s, strs):
    if not s:
      return sorted(strs, key=lambda s: len(s))[0]

    minSoFar = strs[0]
    minDistSoFar = lev(s,strs[0])
    for os in strs[1:]:
      d = lev(s,os)
      if d < minDistSoFar:
        minDistSoFar = d
        minSoFar = os
    return minSoFar

# From Wikipedia
def lev(s, t):
  ''' From Wikipedia article; Iterative with two matrix rows. '''
  if s == t: return 0
  elif len(s) == 0: return len(t)
  elif len(t) == 0: return len(s)
  v0 = [None] * (len(t) + 1)
  v1 = [None] * (len(t) + 1)
  for i in range(len(v0)):
    v0[i] = i
  for i in range(len(s)):
    v1[0] = i + 1
    for j in range(len(t)):
      cost = 0 if s[i] == t[j] else 1
      v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
    for j in range(len(v0)):
      v0[j] = v1[j]
  return v1[len(t)]
