import unittest
import urllib.request
import pickle

class TestUnitPokemons(unittest.TestCase):
    def test_list(self):
        content = urllib.request.urlopen("http://localhost:5000").read()

        file_name = 'test_list.pkl'
        #Код создания дампа html результата
        #with open(file_name, 'wb') as file:
        #    pickle.dump(content,file)
        with open(file_name, 'rb') as file:
            content2 = pickle.load(file)
        self.assertEqual(content, content2)  # add assertion here

    def test_search(self):
        content = urllib.request.urlopen("http://localhost:5000/?search=bulbasaur").read()

        file_name = 'test_search.pkl'
        #Код создания дампа html результата
        #with open(file_name, 'wb') as file:
        #    pickle.dump(content,file)
        with open(file_name, 'rb') as file:
            content2 = pickle.load(file)
        self.assertEqual(content, content2)  # add assertion here

    def test_save(self):
        content = urllib.request.urlopen("http://localhost:5000/ftpsave?selected_pokemon_name=bulbasaur").read()

        file_name = 'test_save.pkl'
        #Код создания дампа html результата
        #with open(file_name, 'wb') as file:
        #    pickle.dump(content,file)
        with open(file_name, 'rb') as file:
            content2 = pickle.load(file)
        self.assertEqual(content, content2)  # add assertion here


if __name__ == '__main__':
    unittest.main()
