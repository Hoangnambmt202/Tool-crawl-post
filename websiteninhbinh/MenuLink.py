
class MenuLink:
    # Constructor method to initialize object attributes
    def __init__(self ):
       
         self.urls =[]  
    # Method to display information about the person
    def add_link(self,link):
        kq = 0
        for item in self.urls:
            if item == link:
                kq = 1
                return 0
        if kq == 0:
            self.urls.append(link)
            return 1
        

    