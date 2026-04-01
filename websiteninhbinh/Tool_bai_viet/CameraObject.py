class CameraObject:
    # Constructor method to initialize object attributes
    def __init__(self,id = 0, name = "",price = 0, url = '',photo = '',cat_id="",date_publish=""):
        self.id = id
        self.name = name
        self.price = price
        self.url = url
        self.description =""
        self.short = ""
        self.tags=""
        self.photos=[]
        self.cat_id = cat_id
        self.date_publish = date_publish
        if photo!= '':
            self.photos.append(photo)

    # Method to display information about the person
    def display_info(self):
        print(f"Name: {self.name},Photo: {self.photos},Price: {self.price}, Url: {self.url}")

        
class Listcam:
    # Constructor method to initialize object attributes
    def __init__(self ):
        self.camobs = []
       
    # Method to display information about the person
    def add_cam(self,obl):
        kq = 0
        # print('add cam:')
        for item in self.camobs:
            # print(item.name + " - " + obl.name)
            if item.name == obl.name or item.url == obl.url:
                kq = 1
                break
        if kq == 0:
            self.camobs.append(obl)
            return 1
        else:
            return 0
        
    def update_cam(self,obl):
        kq = 0
        for item in self.camobs:
            if item.name == obl.name:
                item.description = obl.description
                # item.price = obl.price
                # item.url = obl.url
                kq = 1
        # if kq == 0:
        #     self.camobs.append(obl)

    def display_info(self):
        print(f"Size: {len(self.camobs )} ")