import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

def get_pokemon_list():
    url = "https://pokeapi.co/api/v2/pokemon?limit=100000&offset=0"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if there is an error in the response

        pokemon_list = response.json()["results"]  # Get the list of pokemons
        return pokemon_list

    except requests.exceptions.RequestException as e:
        print("Error occurred while getting the list of pokemons:", e)

def search_pokemon(search_string):
    pokemon_list = get_pokemon_list()
    search_results = []

    for pokemon in pokemon_list:
        if pokemon["name"].lower().startswith(search_string.lower()):
            search_results.append(pokemon)

    return search_results

@app.route('/pokemon')
def pokemon_route():
    pokemon_list = get_pokemon_list()
    return jsonify(pokemon_list)

@app.route('/search', methods=['GET', 'POST'])
def search_route():
    if request.method == 'POST':
        search_query = request.form['search_query']
        search_results = search_pokemon(search_query)
        if search_results:
            return render_template('search_results.html', pokemon_list=search_results)
        else:
            return render_template('search_results.html', error_message='No Pokémon found')

    return render_template('search.html', pokemon_list=get_pokemon_list())

if __name__ == '__main__':
    app.run(debug=True)
