import sqlalchemy
import sqlalchemy.orm as orm
import sqlalchemy.ext.declarative as declarative
import geoalchemy_util
import itertools
import os
import datetime

import alchemy
alchemy_config = alchemy.get_config()
base = declarative.declarative_base()


class RawGoogle(base):
    __tablename__ = 'raw_google'
    id = sqlalchemy.Column("rowid", sqlalchemy.Integer, primary_key=True)
    input_address = sqlalchemy.Column(sqlalchemy.String)
    output_address = sqlalchemy.Column(sqlalchemy.String)
    hierarchy = sqlalchemy.Column(sqlalchemy.String)
    latitude = sqlalchemy.Column(sqlalchemy.REAL)
    longitude = sqlalchemy.Column(sqlalchemy.REAL)

    def __init__(self, input_address, output_address, hierarchy, latitude, longitude):
        self.input_address = input_address
        self.output_address = output_address
        self.hierarchy = hierarchy
        self.latitude = latitude
        self.longitude = longitude

    def __repr__(self):
        return "<RawGoogle('%s','%s','%s','%s','%s')>" % (self.input_address, self.output_address, self.hierarchy, self.latitude, self.longitude)


raw_google_dbpath = os.path.join(
    alchemy_config.get("location").get('path'),
    alchemy_config.get("location").get('database'))
raw_google_engine = sqlalchemy.create_engine('sqlite:///%s' % raw_google_dbpath)
raw_google_session_class = orm.sessionmaker(bind=raw_google_engine)
raw_google_session = raw_google_session_class()


def main(limit=10000, offset=0):
    t = datetime.datetime.now()
    print "geocoding started", t
    #Get all of the raw locations from the XML parsing
    raw_parsed_locations = alchemy.session.query(alchemy.RawLocation).limit(limit).offset(offset)
    if raw_parsed_locations.count() == 0:
        return False
    # raw_parsed_locations = alchemy.session.query(alchemy.RawLocation).filter(alchemy.RawLocation.location_id == None)
    #raw_google_locations = raw_google_session.query(RawGoogle)
    grouped_locations = []
    for instance in raw_parsed_locations:
        #Convert the location into a string that matches the Google format
        parsed_raw_location = geoalchemy_util.concatenate_location(instance.city, instance.state, instance.country)
        cleaned_location = geoalchemy_util.clean_raw_location(parsed_raw_location)
        #Find the location from the raw_google database that matches this input
        matching_location = raw_google_session.query(RawGoogle).filter_by(input_address=cleaned_location).first()
        #alchemy.match(instance)
        if matching_location:
            if(matching_location.latitude != ''):
                grouping_id = "%s|%s" % (matching_location.latitude, matching_location.longitude)
            else:
                grouping_id = "nolocationfound"
                if matching_location.latitude:
                    print matching_location.latitude, matching_location.longitude
            grouped_locations.append({"raw_location": instance,
                                      "matching_location": matching_location,
                                      "grouping_id": grouping_id})
    print "grouped_locations created", datetime.datetime.now() - t
    t = datetime.datetime.now()
    #We now have a list of all locations in the file, along with their
    #matching locations and the id used to group them
    #Sort the list by the grouping_id
    keyfunc = lambda x: x['grouping_id']
    grouped_locations.sort(key=keyfunc)
    grouped_locations_enum = enumerate(itertools.groupby(grouped_locations, keyfunc))
    print "grouped_locations sorted", datetime.datetime.now() - t
    t = datetime.datetime.now()
    match_grouped_locations(grouped_locations_enum)
    #Group by the grouping_id
    
    alchemy.session.commit()

    print "Matches made!", datetime.datetime.now() - t
    print "%s groups formed from %s locations" % (len(grouped_locations), raw_parsed_locations.count())
    
def match_grouped_locations(grouped_locations_enum):
    for i, item in grouped_locations_enum:
        key, grouping = item
        #match_group is the list of RawLocation objects which we call match on
        #We need to get only the RawLocation objects back from the dict
        match_group = []
        #Get the latitude and longitude for the group
        splitkey = key.split('|')
        #The length should be 2
        if len(splitkey) == 2:
            default = {"latitude": splitkey[0], "longitude": splitkey[1]}
        else:
            default = {}
        for grouped_location in grouping:
            match_group.append(grouped_location["raw_location"])

        if len(match_group) > 1:
            # determine most frequent if list of match_group
            most_freq = 0
            for loc in match_group:
                if alchemy.session.query(alchemy.RawLocation).filter(alchemy.RawLocation.id == loc.id).count() > most_freq:
                    default.update(loc.summarize)

        alchemy.match(match_group, alchemy.session, default, commit=False)
        if (i + 1) % alchemy_config.get("location").get("commit_frequency") == 0:
            #print " *", (i + 1), datetime.datetime.now() - t
            alchemy.session.commit()
