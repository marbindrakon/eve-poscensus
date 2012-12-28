# POS Census v0.1
# Copyright (c) 2012 Andrew Austin
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Names and data specific to Eve Online are Copyright CCP Games H.F.

import eveapi
import csv
import sqlite3

# Put your API information here
keyID = XXXXXXX
vCode = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'

# Put the system ID you want to take a census of here
systemID = XXXXXXXXX

def build_database():
    """
    Build a sqlite3 database from the mapDenormalize.csv data file.
    """
    print "Building database...\n"
    conn = sqlite3.Connection("mapData.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE mapDenormalize (id int, name text)''')
    reader = csv.reader(open('mapDenormalize.csv'))
    # Skip the header row
    next(reader)
    # Build a list from which we'll populate the sqlite DB
    records = []
    for row in reader:
        records.append((int(row[0]), row[11]))
    print "Inserting %s rows to mapData.db..." % len(records)
    c.executemany("INSERT INTO mapDenormalize VALUES (?,?)", records)
    conn.commit()
    conn.close()

class POS:
    """
    A POS object, contains a location string, and lists of chas and smas.
    The lists of chas and smas are lists of (itemID, name) tuples.
    """
    def __init__(self, name, location, x, y, z, smas=[], chas=[]):
        self.name = name
        self.location = location
        self.smas = smas
        self.chas = chas
        self.x = x
        self.y = y
        self.z = z

    def report(self):
        """
        Output the report for this POS.
        """
        print "*****************************"
        print "POS: %s at %s" % (self.name, self.location)
        print "\t %s CHAs:" % len(self.chas)
        for cha in self.chas:
            print "\t \t itemID: %s \t Name: %s" % (cha[0], cha[1])
        print "\t %s SMAs:" % len(self.smas)
        for sma in self.smas:
            print "\t \t itemID: %s \t Name: %s" % (sma[0], sma[1])
        print "*****************************"

    def is_owner(self, x, y, z):
        """
        Returns True if the given x,y,z coordinates are within 350km of the POS.
        """
        minx = self.x - 350000
        maxx = self.x + 350000
        miny = self.y - 350000
        maxy = self.y + 350000
        minz = self.z - 350000
        maxz = self.z + 350000
        return minx <= x <= maxx and miny <= y <= maxy and minz <= z <= maxz

def generate_report():
    """
    Main entry point for the program.
    Generates POS objects StarbaseList API and populates them
    using AssetList and Locations API calls.
    """
    api = eveapi.EVEAPIConnection()
    auth = api.auth(keyID=keyID, vCode=vCode)
    conn = sqlite3.Connection('mapData.db')
    c = conn.cursor()
    print "Downloading Corporation Asset List..."
    assets = auth.corp.AssetList()
    print "Downloading Starbase List..."
    starbases = auth.corp.StarbaseList()
    rawCHAList = []
    rawSMAList = []
    poslist = []
    for asset in assets.assets:
        if asset.locationID == systemID:
            if asset.typeID == 17621:
                rawCHAList.append(asset.itemID)
            if asset.typeID == 12237:
                rawSMAList.append(asset.itemID)
    print "Building POS List..."
    for pos in starbases.starbases:
        locationapi = auth.corp.Locations(IDs=pos.itemID).locations[0]
        moon = c.execute("SELECT name from mapDenormalize WHERE id = %s" % pos.moonID).fetchone()[0]
        poslist.append(POS(name=locationapi.itemName,
            location=moon, smas=[], chas=[], x=locationapi.x,
            y=locationapi.y, z=locationapi.z))

    print "Processing SMAs..."
    for sma in rawSMAList:
        locationapi = auth.corp.Locations(IDs=sma).locations[0]
        x = locationapi.x
        y = locationapi.y
        z = locationapi.z
        name = locationapi.itemName
        for pos in poslist:
            if pos.is_owner(x=x, y=y, z=z):
                pos.smas.append((sma, name))

    print "Processing CHAs..."
    for cha in rawCHAList:
        locationapi = auth.corp.Locations(IDs=cha).locations[0]
        x = locationapi.x
        y = locationapi.y
        z = locationapi.z
        name = locationapi.itemName
        for pos in poslist:
            if pos.is_owner(x=x, y=y, z=z):
                pos.chas.append((cha, name))

    print "Displaying Report..."
    for pos in poslist:
        pos.report()

# Make sure we enter at generate_report()
if __name__ == "__main__":
    generate_report()

