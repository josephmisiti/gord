
import os
import pingintel_api
import pprint

from dotenv import load_dotenv

# Load environment variables BEFORE importing any dexter modules
load_dotenv()

address = '1428 west ave miami FL 33139'
pingclient = pingintel_api.PingDataAPIClient(environment="staging", auth_token=os.environ['PING_DATA_STG_AUTH_TOKEN'])
ret = pingclient.enhance(address=address, sources=["PG", "PH"], include_raw_response=True)

pprint.pprint(ret)