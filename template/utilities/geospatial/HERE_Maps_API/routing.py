import requests
import pandas as pd
import json
import base64
import os

# Suppress a specific warning related to not using SSL verify
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request is being made to host")


# Basic API call for getting the driving distance (in meters) and duration (in seconds) for any eligible transport mode
def get_route_info(origin, destination, api_key, transportMode):
    """
    origin and destination should be in a string "latitude,longitude"
    transportMode can be 'pedestrian', 'car', 'truck', 'bicycle' or 'scooter'
    outputs provided are in meters and seconds
    """
    # Checks
    assert transportMode in ['pedestrian', 'car', 'truck', 'bicycle', 'scooter'], "Invalid value for transportMode. Should be one of 'pedestrian', 'car', 'truck', 'bicycle' or 'scooter'"
    
    # Code for requests
    URL = "https://router.hereapi.com/v8/routes"
    PARAMS = {'apikey':api_key,
              'transportMode':transportMode,
              'origin':origin,
              'destination':destination,
              'return':'summary,typicalDuration'} 
    r=requests.get(url=URL,params=PARAMS, verify=False)
    out=r.json()
    return out

#### Example
# get_route_info(get_latlong('6649 N Blue Gum St New Orleans LA',api_key)[0]['string'],
#               get_latlong('1600 pennsylvania ave, Washington, DC',api_key)[0]['string'],api_key, 'car')


#### Wrapper functions for routing
def process_routing(out, summary_only, mile_or_meter):
    # Check successful output
    if out.get('status') is not None:
        return {'duration': None, 'length': None, 'baseDuration': None, 'typicalDuration': None}
    
    if len(out['routes']) == 0:
        return {'duration': None, 'length': None, 'baseDuration': None, 'typicalDuration': None}
    
    if mile_or_meter == "mile":
        out['routes'][0]['sections'][0]['summary']['length'] = out['routes'][0]['sections'][0]['summary']['length'] / 1609.34
    
    if summary_only:
        return out['routes'][0]['sections'][0]['summary']
    else:
        return out

# Driving distance
def get_driving_info(origin, destination, api_key, summary_only=True, mile_or_meter="mile"):
    # Checks
    assert mile_or_meter in ['mile', 'meter'], "Invalid value for mile_or_meter. Should be either 'mile' or 'meter'"
    assert summary_only in [True, False], "Invalid value for summary_only. Should be a Boolean"
    
    out = get_route_info(origin, destination, api_key, 'car')
    
    return process_routing(out, summary_only, mile_or_meter)

# Walking distance
def get_walking_info(origin, destination, api_key, summary_only=True, mile_or_meter="mile"):
    # Checks
    assert mile_or_meter in ['mile', 'meter'], "Invalid value for mile_or_meter. Should be either 'mile' or 'meter'"
    assert summary_only in [True, False], "Invalid value for summary_only. Should be a Boolean"
    
    out = get_route_info(origin, destination, api_key, 'pedestrian')
    
    return process_routing(out, summary_only, mile_or_meter)

# Any routing distance
def get_any_routing_info(origin, destination, api_key, transportMode, summary_only=True, mile_or_meter="mile"):
    # Checks
    assert mile_or_meter in ['mile', 'meter'], "Invalid value for mile_or_meter. Should be either 'mile' or 'meter'"
    assert summary_only in [True, False], "Invalid value for summary_only. Should be a Boolean"
    assert transportMode in ['pedestrian', 'car', 'truck', 'bicycle', 'scooter'], "Invalid value for transportMode. Should be one of 'pedestrian', 'car', 'truck', 'bicycle' or 'scooter'"
    
    out = get_route_info(origin, destination, api_key, transportMode)
    
    return process_routing(out, summary_only, mile_or_meter)



# This code calculate distances between a large number of origins and destinations, using a matrix (pairwise distance) method
# For more configurations, see https://developer.here.com/documentation/matrix-routing-api/api-reference-swagger.html

def calculate_matrix_routing(
    api_key, access_token,
    origins, destinations=None, regionDefinition={"type": "world"}, profile=None, **kwargs):
    """
    origins is a provided as a pandas dataframe with columns "longitude" and "latitude"
    destinations can either be empty (in which case pairwise distances within origins is used) or also a pandas dataframe with columns "longitude" and "latitude"
    
    For regionDefinition, profile and any other arguments, see documentation at https://developer.here.com/documentation/matrix-routing-api/api-reference-swagger.html  
    """

    URL = "https://matrix.router.hereapi.com/v8/matrix?async=false"
    PARAMS = {'apikey': api_key,
              'bearerAuth': access_token
             } 
    
    # Prepare the data
    origins_dict = origins[["latitude", "longitude"]].rename(columns={"latitude":"lat", "longitude":"lng"}).to_dict(orient='records')
    if destinations is not None:
        destinations_dict = destinations[["latitude", "longitude"]].rename(columns={"latitude":"lat", "longitude":"lng"}).to_dict(orient='records')
    else:
        destinations_dict = None
    
    DATA = {
        'origins': origins_dict,
        'regionDefinition': regionDefinition,
        'matrixAttributes': ["travelTimes", "distances"]
    }
    
    if destinations_dict is not None:
        DATA['destinations'] = destinations_dict
    
    if profile is not None:
        DATA['profile'] = profile
    
    if len(kwargs):
        DATA.update(kwargs)
    
    r=requests.post(url=URL,data=json.dumps(DATA),params=PARAMS, verify=False)
    out=r.json()
    
    # Check for errors
    if out.get('status') is not None:
        print("Error: {}".format(out))
        return None
    
    if destinations is None:
        destinations = origins
        
    origins = origins[['latitude', 'longitude']]
    origins['orig_index'] = range(origins.shape[0])
    
    destinations = destinations[['latitude', 'longitude']]
    destinations['dest_index'] = range(destinations.shape[0])
    
    # Cartesian join
    output = pd.merge(origins.assign(key=0), destinations.assign(key=0), on='key').drop('key', axis=1)
    output = output.sort_values(by=['orig_index', 'dest_index'])
    
    output['travelTimes'] = out['matrix']['travelTimes']
    output['distances'] = out['matrix']['distances']
    output['errorCodes'] = 0
    if out['matrix'].get('errorCodes') is not None:
        output['errorCodes'] = out['matrix'].get('errorCodes')
    
    metadata = {
        'matrixId': out['matrixId'],
        'numOrigins': out['matrix']['numOrigins'],
        'numDestinations': out['matrix']['numDestinations'],
        'regionDefinition': out['regionDefinition']
    }
    
    return output, metadata
    
    
# Generate all pairwise combinations between items in a list
def all_combinations(data, data_to = None, unique=True, include_same=False):
    """
    Providing a list or Pandas Series of data, get all unique combinations.
    unique removes duplicates (e.g. #1 paired with #2 is identical to #2 paired with #1)
    include_same keeps self-pairing (e.g. #1 paired with #1) 
    """
    
    if isinstance(data, pd.Series): data = data.tolist()
    dataset1 = pd.DataFrame(data, columns=["Input1"])
    dataset1['Index1'] = range(dataset1.shape[0])
        
    if data_to is None:            
        dataset2 = pd.DataFrame(data, columns=["Input2"])
    else:
        if isinstance(data_to, pd.Series): data_to = data_to.tolist()
        
        dataset2 = pd.DataFrame(data_to, columns=["Input2"])
    dataset2['Index2'] = range(dataset2.shape[0])
       
    # Cartesian join
    output = pd.merge(dataset1.assign(key=0), dataset2.assign(key=0), on='key').drop('key', axis=1)
    output = output.sort_values(by=['Index1', 'Index2'])
    
    if data_to is None:          
        if unique: 
            output = output[output['Index1'] <= output['Index2']]
        
        if not include_same:
            output = output[output['Index1'] != output['Index2']]
        
    output = output.reset_index(drop=True)
    
    return output[["Input1", "Input2", "Index1", "Index2"]]

