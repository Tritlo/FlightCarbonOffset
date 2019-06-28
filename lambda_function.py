import json
from fco import findCO2Kgs

def lambda_handler(event, context):
    fd = findCO2Kgs(json.loads(event['body'])['flights'])

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(fd)
    }
