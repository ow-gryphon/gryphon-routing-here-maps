import requests
import pandas as pd
import json
import base64
import os

# Suppress a specific warning related to not using SSL verify
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request is being made to host")


# Latitude and longitude from address
def get_latlong(address, api_key, summarize=True, limit=1):
    """
    This pulls the latlong associated with an address, as well as more information about the address itself (such as country, state) and the confidence.
    
    The output is a list containing the outputs from the API call, summarized into a simple dictionary if requested. 
    The length of the list depends on how many latitudes/longitudes are requested (using the limit argument), ordered by score.
    
    The 'string' key in the dictionary provides the output in the format "latitude,longitude", and forms the basis for most requests that requires latlong
    """
    
    URL='https://geocode.search.hereapi.com/v1/geocode'
    PARAMS={'apikey':api_key,'q':address, 'limit': limit, 
            'responseattributes': "[matchQuality, matchType, matchCode]"}
    r=requests.get(url=URL,params=PARAMS, verify=False)
    
    if len(r.json()['items']) == 0:
        return [{
                'lat':"", 
                'long':"", 
                'string':"ERROR",
                'country': "", 
                'state': "", 
                'address': "",
                'score': 0}]
    
    out=r.json()['items']
    
    if summarize:
        output = list()
        for i in range(len(out)):
            this_item = out[i]
            
            latitude = this_item['position']['lat']
            longitude = this_item['position']['lng']
            output.append({
                'lat':latitude, 
                'long':longitude, 
                'string':str(latitude)+','+str(longitude),
                'country': this_item['address']['countryName'], 
                'state': this_item['address'].get('state'), 
                'address': this_item['address']['label'],
                'relevance': this_item['scoring']['queryScore'],
                'match_quality_country': this_item['scoring']['fieldScore'].get('country'),
                'match_quality_state': this_item['scoring']['fieldScore'].get('state'),
                'match_quality_district': this_item['scoring']['fieldScore'].get('district'),
                'match_quality_city': this_item['scoring']['fieldScore'].get('city'),
                'match_quality_street': this_item['scoring']['fieldScore'].get('streets')[0] if this_item['scoring']['fieldScore'].get('streets') is not None else None,
                'match_quality_number': this_item['scoring']['fieldScore'].get('houseNumber'),
                'match_quality_postal_code': this_item['scoring']['fieldScore'].get('postalCode'),
            })
        return output
    else:
        return out
        
        
# Latitude and longitude from address. This uses the Geocoding API
def get_latlong_alternative(address, api_key, summarize=True, limit=1):
    """
    This pulls the latlong associated with an address, as well as more information about the address itself (such as country, state) and the confidence.
    
    The output is a list containing the outputs from the API call, summarized into a simple dictionary if requested. 
    The length of the list depends on how many latitudes/longitudes are requested (using the limit argument), ordered by score.
    
    The 'string' key in the dictionary provides the output in the format "latitude,longitude", and forms the basis for most requests that requires latlong
    """
    
    # https://developer.here.com/documentation/geocoding-search-api/dev_guide/topics/endpoint-geocode-brief.html
    URL='https://geocoder.ls.hereapi.com/6.2/geocode.json'
    PARAMS={'apikey':api_key,'searchtext':address}
    
    r=requests.get(url=URL,params=PARAMS, verify=False)
    out=r.json()['Response']['View']
    
    if len(out) == 0:
        return [{
                'lat':"", 
                'long':"", 
                'string':"ERROR",
                'country': "", 
                'state': "", 
                'address': "",
                'relevance': 0}]
    
    if summarize:
        output = list()
        for i in range(min(limit, len(out[0]['Result']))):
            this_item = out[0]['Result'][i]
            
            latitude = this_item['Location']['DisplayPosition']['Latitude']
            longitude = this_item['Location']['DisplayPosition']['Longitude']
            output.append({
                'lat':latitude, 
                'long':longitude, 
                'string':str(latitude)+','+str(longitude),
                'country': this_item['Location']['Address']['Country'], 
                'state': this_item['Location']['Address'].get('State'), 
                'city': this_item['Location']['Address'].get('City'), 
                'address': this_item['Location']['Address']['Label'],
                'relevance': this_item['Relevance'],
                'match_quality_country': this_item['MatchQuality'].get('Country'),
                'match_quality_state': this_item['MatchQuality'].get('State'),
                'match_quality_district': this_item['MatchQuality'].get('District'),
                'match_quality_city': this_item['MatchQuality'].get('City'),
                'match_quality_street': this_item['MatchQuality'].get('Street')[0] if this_item['MatchQuality'].get('Street') is not None else None,
                'match_quality_number': this_item['MatchQuality'].get('HouseNumber'),
                'match_quality_postal_code': this_item['MatchQuality'].get('PostalCode'),
            })
        return output
    else:
        n_results = min(limit, len(out[0]['Results']))
        
        return out[0]['Result'][:n_results]


# Address from latitude and longitude. REVERSE GEOCODE 
def get_address(latlong, api_key, summarize=True, limit=1):
    """
    latlong should be in the format "{latitude},{longitude}" 
    limit is the number of nearest addresses to generate
    
    The output is a list containing the outputs from the API call, summarized into a simple dictionary if requested. 
    The length of the list depends on how many addresses were requested (using the limit argument), ordered by distance to the latlong coordinates.
    
    """
    URL='https://geocode.search.hereapi.com/v1/revgeocode'
    PARAMS={'apikey':api_key,'at':latlong, 'limit':limit}
    r=requests.get(url=URL,params=PARAMS, verify=False)

    if (r.json().get('items') is None) or (len(r.json()['items']) == 0):
        return [
            {
                "address": "",
                "country": "",
                "state": "",
                "city": "",
                "street": "",
                "postalCode": "",
                "latitude": "ERROR",
                "longitude": "ERROR"
            }
        ]
    
    if summarize:
        output = list()
        for i in range(len(r.json()['items'])):
            this_item = r.json()['items'][i]
            this_address = this_item['address']
            output.append({
                "address": this_address['label'],
                "country": this_address['countryName'],
                "state": this_address.get('state'),
                "city": this_address.get('city'),
                "street": this_address.get('street'),
                "postalCode": this_address.get('postalCode'),
                "latitude": this_item['position']['lat'],
                "longitude": this_item['position']['lng']
            })
        return output
        
    else:
        return r.json()['items']


# Find nearby addresses based on filters for type of location
def browse_address(latlong, api_key, categories=None, names=None, summarize=True, limit=1):
    """
    latlong should be in the format "{latitude},{longitude}"
    
    categories should be a comma-separated list of category-Ids from here: https://developer.here.com/documentation/places/dev_guide/topics/place_categories/places-category-system.html 
    names should be a geographic area (country, circular shape, box), see: https://developer.here.com/documentation/geocoding-search-api/api-reference-swagger.html under Browse 
    summarized = True will place the results into a simple dictionary 
    limit is the number of nearest addresses to generate
    
    
    """
    URL='https://geocode.search.hereapi.com/v1/browse'
    PARAMS={'apikey':api_key,'at':latlong, 'limit':limit}
    if categories is not None:
        PARAMS['categories'] = categories
    if names is not None:
        PARAMS['names'] = names
    
    r=requests.get(url=URL,params=PARAMS, verify=False)
    if len(r.json()['items']) == 0:
        return [{
                "address": this_address['label'],
                "country": this_address['countryName'],
                "state": this_address.get('state'),
                "city": this_address.get('city'),
                "street": this_address.get('street'),
                "postalCode": this_address['postalCode'],
                "latitude": this_item['position']['lat'],
                "longitude": this_item['position']['lng']
            }]
    
    if summarize:
        output = list()
        for i in range(len(r.json()['items'])):
            this_item = r.json()['items'][i]
            this_address = this_item['address']
            output.append({
                "address": this_address['label'],
                "country": this_address['countryName'],
                "state": this_address.get('state'),
                "city": this_address.get('state'),
                "street": this_address.get('street'),
                "postalCode": this_address['postalCode'],
                "latitude": this_item['position']['lat'],
                "longitude": this_item['position']['lng'], 
            })
        return output
        
    else:
        return r.json()['items']
    
#### Example usage
# browse_address("38.8789,-76", api_key, limit=2)
# browse_address("38.8789,-76", api_key, categories="600-6100-0062,600-6200-0063", limit=2)