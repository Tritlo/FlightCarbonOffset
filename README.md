# FlightCarbonOffset
Calculates the amount of carbon offset required for given flights by scraping FlightAware and SeatGuru. Site is then hosted on AWS Lambda and AWS S3 through AWS CloudFront.

Alternate implementation uses FlightAware's API, which is severly limited. To run that one, use `awq.py` and set the
`FAApiKey` environment variable to the API key provided by FlightAware.
