from urllib.request import urlopen
from html.parser import HTMLParser

import json

from functools import partial
from statistics import mean

import sys

from common import *

class FAParser(HTMLParser):

  inScript = False
  flightData = None

  def handle_starttag(self, tag, attrs):
    if tag == 'script':
      self.inScript = True

  def handle_endtag(self, tag):
    if tag == 'script':
      self.inScript = False

  def handle_data(self, data):
    if self.inScript:
      # The flight aware page helpfully has data to bootstrap its own data
      bootstr = 'var trackpollBootstrap = '
      if data.startswith(bootstr):
        bsData = data[len(bootstr):-1] # Take the JSON between the start and ;
        self.flightData = json.loads(bsData.replace("\\'", "'"))

class SGSeatParser(HTMLParser):

  inData = None
  seatCount = 0

  def handle_starttag(self,tag,attrs):
    if tag == 'map':
      self.inData = True

    if tag == 'area' and self.inData:
      self.seatCount += 1

  def handle_endtag(self, tag):
    if tag == 'map':
      self.inData = False



def queryFlight(flightCode: str):
  raw = urlopen(f'https://flightaware.com/live/flight/{flightCode}')\
      .read()\
      .decode('utf8')
  parser = FAParser()
  parser.feed(raw)
  if parser.flightData is not None:
    flights = parser.flightData['flights'].values()

    def extract(flight):
      t = flight['aircraft']['type']
      tf = flight['aircraft']['friendlyType']
      plan = flight['flightPlan']
      fuel = plan['fuelBurn']['gallons']
      length = plan['ete']
      return {'type' : t,'friendlyType': tf,
              'gallons':fuel,'flightDuration':length,
              'origin': flight['origin']['friendlyName'],
              'destination': flight['destination']['friendlyName'],
              'distance': plan['directDistance']
      }

    return list(map(extract, flights))
  else:
    raise NoSuchFlightError(flightCode)


class SGPlaneParser(HTMLParser):

  inChart = None
  inNoClassTd = None
  inAirplaneA = None
  makeAndTy = {}
  links = {}
  curLink = None


  def handle_starttag(self,tag,attrs):
    if tag == 'table' and dict(attrs)['id'] in ['comparison','chart']:
      self.inChart = True
    if self.inChart\
       and tag == 'td'\
       and 'class' not in dict(attrs):
      self.inNoClassTd = True

    if self.inChart and self.inNoClassTd and tag == 'a':
      self.inAirplaneA = True
      self.curLink = dict(attrs)['href']


  def handle_endtag(self, tag):
    if tag == 'table':
      self.inChart = False
    if tag =='td':
      self.inNoClassTd = False
    if tag == 'a':
      self.inAirplaneA = False


  def handle_data(self, data):
    if self.inAirplaneA:
      spl = data.split(' ')[:2]
      if len(spl) < 2:
        return
      (m,t) = spl
      if m not in self.makeAndTy:
        self.makeAndTy[m] = {}

      self.makeAndTy[m][t] = self.curLink
      self.links[' '.join(data.split(' ')[:2])] = self.curLink

      self.curLink = None


class SeatQueryer(object):

  cached = None
  aircraft = None
  links = None
  baseUrl = 'https://seatguru.com'

  def loadFromUrl(self):
    lhUrl = 'https://www.seatguru.com/charts/longhaul_economy.php'
    shUrl = 'https://www.seatguru.com/charts/shorthaul_economy.php'

    lhList = urlopen(lhUrl).read().decode('utf8')
    shList = urlopen(shUrl).read().decode('utf8')
    sgpp = SGPlaneParser()
    sgpp.feed(shList)
    sgpp.feed(lhList)
    self.aircraft = sgpp.makeAndTy
    self.links = sgpp.links

  def __init__(self):
    try:
      with open('aircraft.json','r') as f:
        self.cached = json.loads(f.read())
    except FileNotFoundError:
      pass

  @staticmethod
  def transformer(st):
    crj = 'Canadair Regional Jet'
    if st.startswith(crj):
      return 'Bombardier' + st[len(crj):]
    return st

  def findSimilar(self, friendlyType:str):

    friendlyType = self.transformer(friendlyType)
    spl = friendlyType.split(' ')[:2]
    if len(spl) == 2\
       and spl[0] in self.cached\
       and spl[1] in self.cached[spl[0]]:
      return (True, self.cached[spl[0]][spl[1]])

    if not self.aircraft:
      self.loadFromUrl()

    url = None
    minDistStr = None
    if len(spl) == 2 and spl[0] in self.aircraft:
      (m,t) = spl
      if t in self.aircraft[m]:
        minDistStr = t
      else:
        tys = list(self.aircraft[m].keys())
        minDistStr = findMinDistStr(t,tys)
      url = self.aircraft[m][minDistStr]
      if m in self.cached and minDistStr in self.cached[m]:
        return (True, self.cached[m][minDistStr])
      else:
        return (False, url)
    tys = list(self.links.keys())
    minDistStr = findMinDistStr(' '.join(spl),tys)
    url = self.links[minDistStr]
    return (False, url)

  def querySeats(self, friendlyType: str):
    (cached, res) = self.findSimilar(friendlyType)
    if cached:
      return res
    else:
      print(f"{friendlggyType} not cached!")
      raw = urlopen(f'{self.baseUrl}{res}').read().decode('utf8')
      parser = SGSeatParser()
      parser.feed(raw)
      return parser.seatCount

def findCO2Kgs(flights):
  seatQ = SeatQueryer()
  results = {}
  for f in flights:
    data = queryFlight(f)
    results[f] = []
    for r in data:
      seats = seatQ.querySeats(r['friendlyType'])
      (found, simAir) = findSimilar(r['friendlyType'])
      if found:
        seats = round((seats + simAir['seats'])/2)
        #Gallons per mile, and accounting for takeoff and landing
        gEst = int(r['distance'])*simAir['gpm']*1.05
        # Sometimes FlightAware uses both directions at once.
        if r['gallons'] >= 1.5*gEst:
          r['gallons'] = round(max(r['gallons']/2,gEst))
      gps = r['gallons'] / seats
      co2 = round(poundsToKg(gallonsToCO2Pounds(gps)))
      results[f].append({'data': r, 'seats': seats, 'co2': co2, 'gps':gps})
  return results

if __name__ == '__main__':
  flights =  sys.argv[1:]
  results = findCO2Kgs(flights)
  print(results)
  co2Kgs = sum(list(map(lambda x: x['co2'], results.values())))
  gps = sum(list(map(lambda x: x['gps'], results.values())))
  print(f"Total gallons: {gps}")
  print(f"CO2 Kgs: {co2Kgs}")
