# Add Country to the metadata as something to query 

The isin and lei are found with calls to the GLEIF databases.  I wold like the 
application to also get the country code and country of risk from GLEIF as well.  

The country code is taken from the HeadquartersAddress.Country, which represents 
where the operations are, and the country of risk is taken from the LegalJurisdiction,
which represents where the company is registered and which laws apply to them.  They can 
be differenet for offshore accounts, shell companies et cetera.  If the LegalJurisdiction 
has extra characters, such as "US-DL" (for registration in Delaware), just drop everything
after the two first characters for now.  

Please add this information when the database is first loaded from file.  Ammend the 
schema definitoin to include country_code and country_of_risk, both of which are 
ISO 3166-1 alpha-2 codes, ie a two letter code like 'US' for the United States and 'GB' for
Great Britain.  

Please also add this information to the docstring of the search tool, so that the tool 
understands queries about the country information.


'''
Note: When filtering by country, use ISO 3166-1 alpha-2 codes (e.g., "WHERE c.country_code = 'US'").
'''

