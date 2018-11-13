import requests
import json
import pg8000

# The following mock client imitates the CLI during the onboarding scenario for new images.
# The expectation is that the CLI uploads images to a temporary blob store, then gets a list 
# of URLs to those images and passes the list to an HTTP trigger function in the format of
# a JSON string.  The HTTP trigger function creates rows in the database for the images,
# retrieves the ImageId's for them, and then copies the images, each renamed as "ImageId.extension",
# into a permanent blob storage container.  The HTTP function returns the list of URLs to
# the images in permanent blob storage.

print("\nTest client for CLI Onboarding scenario")
print('-' * 40)

# functionURL = "https://onboardinghttptrigger.azurewebsites.net/api/onboarding?code=lI1zl4IhiHcOcxTS85RsE7yZJXeNRxnr7tXSO1SrLWdpiN0W6hT3Jw=="
functionURL = "http://localhost:7071/api/onboarding"
# Sean's function URL:
# functionURL = "https://onboardinghttptrigger.azurewebsites.net/api/onboarding?code=lI1zl4IhiHcOcxTS85RsE7yZJXeNRxnr7tXSO1SrLWdpiN0W6hT3Jw=="
# functionURL = "https://abrig-linux-func.azurewebsites.net/api/onboarding"

urlList = { "imageUrls": ["https://akaonboardingstorage.blob.core.windows.net/aka-temp-source-container/puppies1.jpg",
                         "https://akaonboardingstorage.blob.core.windows.net/aka-temp-source-container/puppies2.jpg",
                         "https://akaonboardingstorage.blob.core.windows.net/aka-temp-source-container/puppies3.jpg"] }

headers = {"Content-Type": "application/json"}

print("Now executing POST request to onboard images...to:")
print("Function URL: " + functionURL)
print("Headers:")
for key, value in headers.items():
    print("\t" + key + ": " + value)
response = requests.post(url=functionURL, headers=headers, json=urlList)
print("Completed POST request.")

raw_response = response.text
response_array = raw_response.split(", ")
response_output = "\n".join(response_array)

print(f"Response status code: {response.status_code}")
print(f"Response string: {response_output}")