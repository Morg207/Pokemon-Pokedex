import customtkinter as ctk
import threading
from PIL import Image, ImageSequence
import io
import requests

class Pokedex:
    def __init__(self):
        ctk.set_default_color_theme("dark-blue")
        ctk.set_appearance_mode("dark")
        self.window = ctk.CTk()
        self.window.title("Pokedex 1.0")
        self.frames = []
        self.pokemon_index = 0
        self.frame_index = 0
        self.build_ui()
        self.pokemon_urls = Pokedex.get_pokemon_urls()
        threading.Thread(target=self.get_pokemon_data, daemon=True).start()
        self.run_pokemon_animation()

    def build_ui(self):
        bg_colour = ctk.ThemeManager.theme["CTk"]["fg_color"]
        self.window_frame = ctk.CTkFrame(self.window, fg_color=bg_colour)
        self.window_frame.pack(padx=20, pady=20, fill="both", expand=True)
        self.create_welcome_label()
        self.create_entry()
        self.create_data_labels(bg_colour)
        self.create_buttons()

    def create_welcome_label(self):
        self.welcome_label = ctk.CTkLabel(self.window_frame, text="Welcome to Pokedex version 1.0!", font=("Arial", 14))
        self.welcome_label.pack(pady=(0, 20))

    def create_entry(self):
        self.pokemon_entry = ctk.CTkEntry(self.window_frame, placeholder_text="Search for pokemon...",
                                          width=400, height=40, justify="center", font=("Arial", 20),
                                          placeholder_text_color="white", text_color="white")
        self.pokemon_entry.bind("<Return>", self.search_for_pokemon)
        self.pokemon_entry.pack()

    def create_data_labels(self, bg_colour):
        self.image_label = ctk.CTkLabel(self.window_frame, width=230, height=230, text="Loading image...",
                                        font=("Arial", 30))
        self.image_label.pack(pady=(25, 0))
        self.name_label = ctk.CTkLabel(self.window_frame, text="", font=("Arial", 20))
        self.ability_label = ctk.CTkLabel(self.window_frame, text="", font=("Arial", 20))
        self.type_label = ctk.CTkLabel(self.window_frame, text="", font=("Arial", 20))
        self.name_label.pack(pady=(20, 5))
        self.ability_label.pack(pady=(0, 5))
        self.type_label.pack(pady=(0, 10))

    def create_buttons(self):
        button_frame = ctk.CTkFrame(self.window_frame)
        self.backward_button = ctk.CTkButton(button_frame, text="Backward", width=40, font=("Arial", 17),
                                             state="disabled", command=self.backward)
        self.forward_button = ctk.CTkButton(button_frame, text="Forward", width=40, font=("Arial", 17),
                                            state="disabled", command=self.forward)
        self.backward_button.pack(side="left", padx=(0, 10))
        self.forward_button.pack(side="right")
        button_frame.pack(pady=(10, 0))

    def run_pokedex(self):
        self.window.mainloop()

    def clamp_pokemon_index(self):
        pokemon_index = max(0, min(self.pokemon_index, len(self.pokemon_urls)-1))
        return pokemon_index

    def load_pokemon_images(self, pokemon_attributes):
        image_url = Pokedex.get_image_url(pokemon_attributes)
        if not image_url:
             self.image_label.configure(text="No image available...")
             return
        image_response = requests.get(image_url)
        pokemon_image = Image.open(io.BytesIO(image_response.content)) #We have to wrap content (the raw image bytes) sent from the network in a bytes IO object so pillow can decode the raw image bytes.
        self.frames = []                                               #BytesIO object allows the bytes to be read as a stream. Once the raw image bytes have been decoded into a gif, it's useable. 
        for frame in ImageSequence.Iterator(pokemon_image): #This is just pillows way of extracting individual images from the gif.
            resized_frame = frame.convert("RGBA").resize((230, 230), Image.Resampling.NEAREST) #Nearest neighbour resampling. Good for resizing pixel art sprites and graphics. 
            ctk_frame = ctk.CTkImage(light_image=resized_frame, dark_image=resized_frame, size=(230, 230)) 
            self.frames.append(ctk_frame)

    def get_pokemon_data(self):
        self.frame_index = 0
        if not self.pokemon_urls:
            self.image_label.configure(text="No Pokémon found...")
            return
        pokemon_data = self.pokemon_urls[self.pokemon_index]
        pokemon_attributes = Pokedex.get_pokemon_details(pokemon_data["url"])
        self.load_pokemon_images(pokemon_attributes)
        self.window.after(0, lambda: self.update_interface(pokemon_attributes))

    def update_interface(self, attributes):
        name = attributes["name"].capitalize()
        abilities = attributes["abilities"]
        types = attributes["types"]
        ability_text = f"Abilities: {abilities[0]['ability']['name']}"
        if len(abilities) > 1:
            ability_text += f" - {abilities[1]['ability']['name']}"
        type_text = "Type: " + " - ".join([type['type']['name'] for type in types])
        self.update_widgets(name, ability_text, type_text)

    def update_widgets(self, name, ability_text, type_text):
        self.image_label.configure(text="")
        self.name_label.configure(text=name)
        self.ability_label.configure(text=ability_text)
        self.type_label.configure(text=type_text)
        if self.pokemon_index != 0:
            self.backward_button.configure(state="enabled")
        if self.pokemon_index != len(self.pokemon_urls)-1:
            self.forward_button.configure(state="enabled")

    def run_pokemon_animation(self):
        if self.frames:
            self.frame_index %= len(self.frames)
            self.image_label.configure(image=self.frames[self.frame_index])
            self.frame_index += 1
        self.image_label.after(100, self.run_pokemon_animation) #Keep running this code on the gui thread periodically.

    def forward(self):
        self.pokemon_index += 1
        self.pokemon_index = self.clamp_pokemon_index()
        if self.pokemon_index == len(self.pokemon_urls)-1:
            self.backward_button.configure(state="enabled")
            self.forward_button.configure(state="disabled")
        else:
            self.backward_button.configure(state="disabled")
            self.forward_button.configure(state="disabled")
        threading.Thread(target=self.get_pokemon_data, daemon=True).start() #Running this on a new thread so network requests won't freeze the application animations.
                                                                            #It's a daemon thread because it's non-important. If the user closes the application, I want this thread to kill itself, not wait to finish.
    def backward(self):
        self.pokemon_index -= 1
        self.pokemon_index = self.clamp_pokemon_index()
        self.backward_button.configure(state="disabled")
        self.forward_button.configure(state="disabled")
        threading.Thread(target=self.get_pokemon_data, daemon=True).start()

    def search_for_pokemon(self, event=None):
        text_input = self.pokemon_entry.get().lower()
        for index, pokemon in enumerate(self.pokemon_urls):
            if pokemon["name"] == text_input:
                if self.pokemon_index == index: #If a pokemon name has already been searched and the user presses enter again, it won't make a needless network request.
                    return
                self.pokemon_index = index
                self.backward_button.configure(state="disabled")
                self.forward_button.configure(state="disabled")
                threading.Thread(target=self.get_pokemon_data, daemon=True).start()
                return

    @staticmethod
    def get_pokemon_urls():
        url = "https://pokeapi.co/api/v2/pokemon?limit=151"
        response = requests.get(url)
        if response.status_code != 200: #HTTP spec says if error code other than 200, something went wrong.
            return []
        return response.json()["results"]

    @staticmethod
    def get_pokemon_details(url):
        response = requests.get(url)
        if response.status_code != 200:
            return {}
        return response.json()

    @staticmethod
    def get_image_url(pokemon_attributes):
        sprites = pokemon_attributes.get("sprites", {})
        versions = sprites.get("versions", {})
        gen_v = versions.get("generation-v", {})
        black_white = gen_v.get("black-white", {})
        animated = black_white.get("animated", {})
        image_url = animated.get("front_default")
        return image_url

if __name__ == "__main__":
    pokedex = Pokedex()
    pokedex.run_pokedex()

