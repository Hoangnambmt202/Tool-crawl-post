
class ObjectLink:
    # Constructor method to initialize object attributes
    def __init__(self,id =0, name = "",price=0):
        self.id = id
        self.name = name
        self.price = price
        self.cobs = []
    # Method to display information about the person
    def add_cam(self,cob):
        kq = 0
        for item in self.cobs:
            if item.name == cob.name:
                kq = 1
                break
        if kq != 0:
            self.cobs.append(cob)

    def display_info(self):
        print(f"Name: {self.name},Price: {self.price}, Url: {self.url}")

class Listoblink:
    # Constructor method to initialize object attributes
    def __init__(self ):
        self.obls = []
       
    # Method to display information about the person
    def add_link(self,obl):
        kq = 0
        for item in obls:
            if item.name == obl.name:
                kq = 1
                break
        if kq != 0:
            obls.append(obl)

    def display_info(self):
        print(f"Size: {self.obls.length} ")