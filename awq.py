#!//usr/bin/env python3

import requests
import json

import os

from common import *

username = "tritlo"

fxmlUrl = "https://flightxml.flightaware.com/json/FlightXML3/"

with open('aircraft-2.0.json','r') as f:
  aircraftInfo = json.loads(f.read())

# Fix inconsistencies in naming from FlightAware
def transformer(st):
  crj = 'Canadair Regional Jet'
  if st.startswith(crj):
    return 'Bombardier' + st[len(crj):]
  return st

def findSimilar(friendlyType:str):

  friendlyType = transformer(friendlyType)
  spl = friendlyType.split(' ')[:2]
  if len(spl) == 2\
     and spl[0] in aircraftInfo\
     and spl[1] in aircraftInfo[spl[0]]:
    return (True, aircraftInfo[spl[0]][spl[1]])

  if len(spl) == 2 and spl[0] in aircraftInfo:
    (m,t) = spl
    if t in aircraftInfo[m]:
      minDistStr = t
    else:
      tys = list(aircraftInfo[m].keys())
      minDistStr = findMinDistStr(t,tys)
    return (True, aircraftInfo[m][minDistStr])

  return (False, None)


def queryFlight(ident):
  apiKey = os.environ.get('FAApiKey')
  payload = {'ident':ident}
  response = requests.get(fxmlUrl + "FlightInfoStatus",
                          params=payload,
                          auth=(username, apiKey))
  res = response.json()
  flights = res["FlightInfoStatusResult"]["flights"]
  # We only check the first one, to avoid too many
  # API requests for aircraft....

  origin = flights[0]["origin"]["airport_name"]
  destination = flights[0]["destination"]["airport_name"]
  aircraft = flights[0]["aircrafttype"]
  distance = int(flights[0]["distance_filed"])
  duration = int(flights[0]["filed_ete"])
  payload = {'type': aircraft}
  r2 = requests.get(fxmlUrl + "AircraftType",
                    params=payload,
                    auth=(username, apiKey))

  res = r2.json()["AircraftTypeResult"]
  manufacturer = res["manufacturer"]
  aircraftType = res["type"]
  ft = ' '.join([manufacturer,aircraftType])
  (found, acinfo) = findSimilar(ft)

  # We couldn't find that type of airplane
  if not found:
    raise NoSuchFlightError(ident)
  return {'type': aircraft,
          'friendlyType': ft,
          'flightDuration': duration,
          'origin': origin,
          'destination': destination,
          'distance': distance,
          'gallons': round((distance * acinfo['gpm'])),
          'gps': round((distance * acinfo['gpmps'])),
          'seats': acinfo['seats']
        }


def findCO2Kgs(flights):
  results = {}
  for f in flights:
    data = queryFlight(f)
    results[f] = []
    seats = data['seats']
    gps = data['gps']
    co2 = round(poundsToKg(gallonsToCO2Pounds(gps)))
    results[f].append({'data': data, 'seats': seats, 'co2': co2, 'gps':gps})

  return results

if __name__ == '__main__':
  print(findCO2Kgs(['UA9916','FI216']))




