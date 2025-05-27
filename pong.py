#test
#includeer bibliotheken
import pygame
import sys
import random
import math
import os
from paho.mqtt import client as mqtt_client

#initialiseer Pygame en Pygame mixer
pygame.init()
pygame.mixer.init()

#MQTT variabelen
broker = '192.168.0.157'
port = 1883
topic = "GAME/milo"
client_id_base = "esp32-pong-receiver-"
paddle_mqtt_target_move = 0
mqtt_client_instance = None

#variabelen voor bestruringsmodus
CONTROL_MODE_MQTT = "MQTT"
CONTROL_MODE_KEYBOARD = "KEYBOARD"
current_control_mode = CONTROL_MODE_MQTT

#MQTT connectie
def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(topic)
        print(f"Subscribed to topic: {topic}")
    else:
        print(f"Failed to connect to MQTT, return code {rc}\n")

#MQTT berichtverwerking
def on_mqtt_message(client, userdata, msg):
    global paddle_mqtt_target_move
    payload = msg.payload.decode()

    if payload == "0;1":      
        paddle_mqtt_target_move = -1
    elif payload == "1;0":    
        paddle_mqtt_target_move = 1
    elif payload == "0;0":    
        paddle_mqtt_target_move = 0
    elif payload == "1;1":    
        paddle_mqtt_target_move = 0

#MQTT setup
def setup_mqtt_client():
    global mqtt_client_instance
    unique_client_id = f"{client_id_base}{random.randint(0, 10000)}"
    
    try:
        mqtt_client_instance = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1, unique_client_id)
    except AttributeError:
        print("Paho-MQTT < 1.6.0 detected, using older Client constructor.")
        mqtt_client_instance = mqtt_client.Client(unique_client_id)
    
    mqtt_client_instance.on_connect = on_mqtt_connect
    mqtt_client_instance.on_message = on_mqtt_message

    try:
        print(f"Attempting to connect to MQTT broker {broker}:{port} with client ID {unique_client_id}")
        mqtt_client_instance.connect(broker, port, 60)
        mqtt_client_instance.loop_start()
    except ConnectionRefusedError:
        print(f"MQTT Connection Refused. Is the broker running at {broker}:{port}?")
        mqtt_client_instance = None
    except OSError as e:
        print(f"MQTT OS Error: {e}. Check network connection and broker address.")
        mqtt_client_instance = None
    except Exception as e:
        print(f"An unexpected error occurred during MQTT setup: {e}")
        mqtt_client_instance = None

#variabelen voor schermgrootte
GAME_AREA_WIDTH = 400
GAME_AREA_HEIGHT = 400
INFO_PANEL_WIDTH = 250
SCREEN_WIDTH = GAME_AREA_WIDTH + INFO_PANEL_WIDTH
SCREEN_HEIGHT = GAME_AREA_HEIGHT

#kleuren
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
LIGHT_GREY = (200, 200, 200)

#initialiseer lettertypen
font_groot = pygame.font.Font(None, 36)
font_klein = pygame.font.Font(None, 28)
font_mini = pygame.font.Font(None, 24) # Gebruikt voor highscore items
font_countdown = pygame.font.Font(None, 100) 

#initialiseer background geluid
channel1 = pygame.mixer.Channel(0)
try:
    background_sound = pygame.mixer.Sound('yes.mp3')
    channel1.play(background_sound, -1)
except pygame.error as e:
    print(f"Kon achtergrondgeluid niet laden/afspelen: {e}")

#initialiseer bounce geluid
channel2 = pygame.mixer.Channel(1)
bounce_sound = None 
try:
    bounce_sound = pygame.mixer.Sound('bounce.mp3')
    channel2.set_volume(2)
except pygame.error as e:
    print(f"Kon bounce geluid niet laden: {e}")

#highscore bestand
HIGHSCORE_FILE = "highscores.txt"
highscoresEASY = []
highscoresMEDIUM = []
highscoresHARD = []

#functie om highscores te laden
def laad_highscores():
    global highscoresEASY, highscoresMEDIUM, highscoresHARD
    highscoresEASY = []
    highscoresMEDIUM = []
    highscoresHARD = []
    if os.path.exists(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, 'r') as f:
                for line in f:
                    parts = line.strip().split(';')
                    if len(parts) == 3:
                        level, naam, tijd_str = parts
                        try:
                            tijd = float(tijd_str)
                            if level == "Easy":
                                highscoresEASY.append({'level': level, 'naam': naam, 'tijd': tijd})
                            elif level == "Medium":
                                highscoresMEDIUM.append({'level': level, 'naam': naam, 'tijd': tijd})
                            elif level == "Hard":
                                highscoresHARD.append({'level': level, 'naam': naam, 'tijd': tijd})
                        except ValueError:
                            print(f"Ongeldige data in highscore bestand (tijd): {tijd_str}")
        except IOError as e:
            print(f"Fout bij lezen highscore bestand: {e}")
    highscoresEASY.sort(key=lambda x: x['tijd'], reverse=True)
    highscoresMEDIUM.sort(key=lambda x: x['tijd'], reverse=True)
    highscoresHARD.sort(key=lambda x: x['tijd'], reverse=True)

#functie om highscores op te slaan
def sla_highscores_op():
    global highscoresEASY, highscoresMEDIUM, highscoresHARD
    
    all_scores_to_save = highscoresEASY + highscoresMEDIUM + highscoresHARD
    
    try:
        with open(HIGHSCORE_FILE, 'w') as f:
            for score in all_scores_to_save:
                f.write(f"{score['level']};{score['naam']};{score['tijd']:.2f}\n")
    except IOError as e:
        print(f"Fout bij schrijven highscore bestand: {e}")

#functie om een highscore toe te voegen
def voeg_highscore_toe(level, naam, tijd):
    global highscoresEASY, highscoresMEDIUM, highscoresHARD
    
    new_score = {'level': level, 'naam': naam, 'tijd': tijd}
    
    if level == "Easy":
        highscoresEASY.append(new_score)
        highscoresEASY.sort(key=lambda x: x['tijd'], reverse=True)
        highscoresEASY = highscoresEASY[:10]
    elif level == "Medium":
        highscoresMEDIUM.append(new_score)
        highscoresMEDIUM.sort(key=lambda x: x['tijd'], reverse=True)
        highscoresMEDIUM = highscoresMEDIUM[:10]
    elif level == "Hard":
        highscoresHARD.append(new_score)
        highscoresHARD.sort(key=lambda x: x['tijd'], reverse=True)
        highscoresHARD = highscoresHARD[:10]
    else:
        print(f"Poging tot toevoegen highscore voor onbekend level: {level}")
        return

    sla_highscores_op()

#laad opgeslagen highscores
laad_highscores()

#klasse voor knoppen
class Button:
    def __init__(self, x, y, width, height, color, text, action, text_font=font_groot):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.text = text
        self.action = action
        self.text_font = text_font

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        text_surface = self.text_font.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

#variabelen voor spelstatus
game_state = "NAAM_INVOER" 
huidige_paddle_hoogte = 40
doel_bal_snelheid = 0
huidige_level_naam = ""
speler_naam = ""
speler_naam_input_active = True

#spel variabelen
levens = 3
sessie_start_tijd = 0
totale_speeltijd_sessie = 0.0
countdown_end_time = 0 

#variabelen voor bal
ball_radius = 8
ball_x, ball_y = GAME_AREA_WIDTH // 4, GAME_AREA_HEIGHT // 2
ball_speed_x, ball_speed_y = 0, 0

#paddle variabelen
PADDLE_WIDTH = 5
paddle_x = GAME_AREA_WIDTH - PADDLE_WIDTH - 10
paddle_y = (GAME_AREA_HEIGHT // 2) - (huidige_paddle_hoogte // 2)
PADDLE_SPEED = 7

#dikte van de randen
THICKNESS = 4

#functie om de bal positie te resetten
def reset_ball_position_and_zero_speed():
    global ball_x, ball_y, ball_speed_x, ball_speed_y
    ball_x = GAME_AREA_WIDTH // 4
    ball_y = random.randrange(ball_radius + THICKNESS, GAME_AREA_HEIGHT - ball_radius - THICKNESS)
    ball_speed_x = 0
    ball_speed_y = 0

#functie om de bal te lanceren met een random hoek
def launch_ball():
    global ball_speed_x, ball_speed_y, doel_bal_snelheid
    
    angle_rad = random.uniform(-math.pi / 8, math.pi / 8) 
    
    candidate_ball_speed_x = doel_bal_snelheid * math.cos(angle_rad)
    candidate_ball_speed_y = doel_bal_snelheid * math.sin(angle_rad)

    ball_speed_y = candidate_ball_speed_y

    if candidate_ball_speed_x <= 0:
        if doel_bal_snelheid > 0: 
            ball_speed_x = abs(doel_bal_snelheid * math.cos(angle_rad))
        else: 
            ball_speed_x = 0.1
    else: 
        ball_speed_x = candidate_ball_speed_x

#functie om de bal te resetten voor een nieuwe beurt
def reset_bal_voor_nieuwe_beurt(): 
    reset_ball_position_and_zero_speed()
    launch_ball()

#functie om de spelstatus voor de countdown
def prepare_for_countdown():
    global game_state, levens, totale_speeltijd_sessie, paddle_y
    global countdown_end_time, sessie_start_tijd, huidige_paddle_hoogte

    levens = 3
    sessie_start_tijd = 0 
    totale_speeltijd_sessie = 0.0
    
    paddle_y = (GAME_AREA_HEIGHT // 2) - (huidige_paddle_hoogte // 2)
    reset_ball_position_and_zero_speed() 
    
    game_state = "COUNTDOWN"
    countdown_end_time = pygame.time.get_ticks() + 3000 

#functie voor de eerste knop(easy)
def button_easy_action():
    global doel_bal_snelheid, huidige_paddle_hoogte, huidige_level_naam
    doel_bal_snelheid = 2
    huidige_paddle_hoogte = 60
    huidige_level_naam = "Easy"
    prepare_for_countdown()

#functie voor de tweede knop(medium)
def button_medium_action():
    global doel_bal_snelheid, huidige_paddle_hoogte, huidige_level_naam
    doel_bal_snelheid = 4
    huidige_paddle_hoogte = 50
    huidige_level_naam = "Medium"
    prepare_for_countdown()

#functie voor de derde knop(hard)
def button_hard_action():
    global doel_bal_snelheid, huidige_paddle_hoogte, huidige_level_naam
    doel_bal_snelheid = 6
    huidige_paddle_hoogte = 40
    huidige_level_naam = "Hard"
    prepare_for_countdown()

#knoppen voor moeilijkheidsgraad
difficulty_buttons = [
    Button(SCREEN_WIDTH // 2 - 75, 150, 150, 50, BLUE, "Easy", button_easy_action),
    Button(SCREEN_WIDTH // 2 - 75, 220, 150, 50, RED, "Medium", button_medium_action),
    Button(SCREEN_WIDTH // 2 - 75, 290, 150, 50, GREEN, "Hard", button_hard_action),
]

#creeer het scherm
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Pong")
clock = pygame.time.Clock()

#functie om de hoek te berekenen
def hoek_berekenen_rad(bol_raak_y, plankje_y, plankje_hoogte):
    relatieve_inslag_op_plankje = bol_raak_y - plankje_y
    plankje_midden_relatief = plankje_hoogte / 2
    verschil_met_midden = relatieve_inslag_op_plankje - plankje_midden_relatief
    
    if plankje_hoogte == 0: return 0
    
    norm_diff = verschil_met_midden / (plankje_hoogte / 2)
    norm_diff = max(-1.0, min(1.0, norm_diff)) 
    
    max_angle_rad = math.radians(60)  
    berekende_hoek_rad = norm_diff * max_angle_rad
        
    return berekende_hoek_rad

#functie om het speelveld te tekenen
def draw_speelveld():
    pygame.draw.line(screen, BLUE, (0, THICKNESS // 2), (GAME_AREA_WIDTH, THICKNESS // 2), THICKNESS)
    pygame.draw.line(screen, BLUE, (0, GAME_AREA_HEIGHT - THICKNESS // 2), (GAME_AREA_WIDTH, GAME_AREA_HEIGHT - THICKNESS // 2), THICKNESS)
    pygame.draw.line(screen, BLUE, (THICKNESS // 2, 0), (THICKNESS // 2, GAME_AREA_HEIGHT), THICKNESS)
    pygame.draw.circle(screen, WHITE, (int(ball_x), int(ball_y)), ball_radius)
    pygame.draw.rect(screen, WHITE, (paddle_x, paddle_y, PADDLE_WIDTH, huidige_paddle_hoogte))

#functie om de info paneel te tekenen
def draw_info_paneel():
    global current_control_mode
    info_x_start = GAME_AREA_WIDTH + 10
    pygame.draw.line(screen, LIGHT_GREY, (GAME_AREA_WIDTH, 0), (GAME_AREA_WIDTH, SCREEN_HEIGHT), 2)

    # Basisinfo
    current_y = 20 # Start y-positie voor info
    level_text_surf = font_klein.render(f"Level: {huidige_level_naam}", True, WHITE)
    screen.blit(level_text_surf, (info_x_start, current_y))
    current_y += level_text_surf.get_height() + 5 # Verhoog y na elk item

    naam_text_surf = font_klein.render(f"Speler: {speler_naam}", True, WHITE)
    screen.blit(naam_text_surf, (info_x_start, current_y))
    current_y += naam_text_surf.get_height() + 5

    beurten_text_surf = font_klein.render(f"Beurten: {levens}/3", True, WHITE)
    screen.blit(beurten_text_surf, (info_x_start, current_y))
    current_y += beurten_text_surf.get_height() + 5
    
    current_play_time = totale_speeltijd_sessie
    if game_state == "SPELEN" and sessie_start_tijd > 0:
         current_play_time = (pygame.time.get_ticks() - sessie_start_tijd) / 1000.0
    elif game_state != "SPELEN": 
         current_play_time = 0.0

    tijd_minuten = int(current_play_time // 60)
    tijd_seconden = int(current_play_time % 60)
    tijd_text_surf = font_klein.render(f"Tijd: {tijd_minuten:02d}:{tijd_seconden:02d}", True, WHITE)
    screen.blit(tijd_text_surf, (info_x_start, current_y))
    current_y += tijd_text_surf.get_height() + 10 # Iets meer padding voor highscore sectie

    # Highscores sectie
    hs_title_text_surf = font_klein.render("Highscores:", True, WHITE)
    screen.blit(hs_title_text_surf, (info_x_start, current_y))
    current_y += hs_title_text_surf.get_height() + 5 
    
    gamemodes_data = [
        ("Easy:", highscoresEASY),
        ("Medium:", highscoresMEDIUM),
        ("Hard:", highscoresHARD)
    ]

    padding_after_gamemode_title = 2
    padding_between_scores = 0 
    padding_after_gamemode_section = 8
    score_indent = 15

    for title_str, scores_list in gamemodes_data:
        gamemode_title_surf = font_mini.render(title_str, True, LIGHT_GREY)
        screen.blit(gamemode_title_surf, (info_x_start, current_y))
        current_y += gamemode_title_surf.get_height() + padding_after_gamemode_title

        for i, score_data in enumerate(scores_list[:3]): # Toon top 3
            speler = score_data['naam'][:8] if score_data['naam'] else 'Anon'
            tijd_min = int(score_data['tijd'] // 60)
            tijd_sec = int(score_data['tijd'] % 60)
            score_str = f"{i+1}. {speler} {tijd_min:02d}:{tijd_sec:02d}"
            score_item_surf = font_mini.render(score_str, True, LIGHT_GREY)
            screen.blit(score_item_surf, (info_x_start + score_indent, current_y))
            current_y += score_item_surf.get_height() + padding_between_scores
        
        current_y += padding_after_gamemode_section # Ruimte voor de volgende gamemode of control text

    # Control mode tekst
    control_mode_text_str = f"Control (K): {current_control_mode}"
    control_mode_surf = font_mini.render(control_mode_text_str, True, WHITE)
    
    # Toon alleen als er nog ruimte is binnen het paneel
    if current_y + control_mode_surf.get_height() < SCREEN_HEIGHT - 5: # 5px marge van onderkant
        screen.blit(control_mode_surf, (info_x_start, current_y))


#functie om de naam invoer scherm te tekenen
def draw_naam_invoer_scherm():
    screen.fill(BLACK)
    titel_text = font_groot.render("Voer je naam in:", True, WHITE)
    titel_rect = titel_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
    screen.blit(titel_text, titel_rect)

    input_rect_breedte = 300
    input_rect_hoogte = 50
    input_rect = pygame.Rect(SCREEN_WIDTH // 2 - input_rect_breedte // 2, 150, input_rect_breedte, input_rect_hoogte)
    pygame.draw.rect(screen, WHITE, input_rect, 2)

    naam_surface = font_groot.render(speler_naam, True, WHITE)
    screen.blit(naam_surface, (input_rect.x + 10, input_rect.y + 10))

    info_text = font_klein.render("Druk op Enter om te bevestigen", True, LIGHT_GREY)
    info_rect = info_text.get_rect(center=(SCREEN_WIDTH // 2, input_rect.bottom + 30))
    screen.blit(info_text, info_rect)

#functie om het moeilijkheidsgraad menu te tekenen
def draw_moeilijkheid_menu():
    screen.fill(BLACK)
    titel_text = font_groot.render("Kies moeilijkheidsgraad", True, WHITE)
    titel_rect = titel_text.get_rect(center=(SCREEN_WIDTH // 2, 80))
    screen.blit(titel_text, titel_rect)
    for button in difficulty_buttons:
        button.draw(screen)

#functie om het einde scherm te tekenen
def draw_sessie_einde_scherm():
    screen.fill(BLACK) 
    
    einde_text_str = "Sessie voorbij!"
    if levens == 0:
        final_time_min = int(totale_speeltijd_sessie // 60)
        final_time_sec = int(totale_speeltijd_sessie % 60)
        einde_text_str = f"Alle beurten op! Tijd: {final_time_min:02d}:{final_time_sec:02d}"
    
    einde_text = font_groot.render(einde_text_str, True, WHITE)
    einde_rect = einde_text.get_rect(center=(GAME_AREA_WIDTH // 2, SCREEN_HEIGHT // 2 - 30))
    screen.blit(einde_text, einde_rect)

    info_text = font_klein.render("Klik om opnieuw te beginnen", True, LIGHT_GREY)
    info_rect = info_text.get_rect(center=(GAME_AREA_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))
    screen.blit(info_text, info_rect)

#stel MQTT client in
if mqtt_client_instance is None:
    setup_mqtt_client() 

#start de game loop
running = True
while running:
    #alle gebruikersinvoer en systeemevenementen
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_k: 
                current_control_mode = CONTROL_MODE_KEYBOARD if current_control_mode == CONTROL_MODE_MQTT else CONTROL_MODE_MQTT
                print(f"Switched to {current_control_mode} control")

        if game_state == "NAAM_INVOER":
            if event.type == pygame.KEYDOWN:
                if speler_naam_input_active:
                    if event.key == pygame.K_RETURN:
                        if len(speler_naam.strip()) > 0:
                            speler_naam_input_active = False
                            game_state = "MENU_DIFFICULTY"
                        else:
                            speler_naam = "" 
                    elif event.key == pygame.K_BACKSPACE:
                        speler_naam = speler_naam[:-1]
                    elif len(speler_naam) < 15: 
                        if event.unicode.isalnum() or event.unicode == ' ':
                            speler_naam += event.unicode
        
        elif game_state == "MENU_DIFFICULTY":
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: 
                    for button in difficulty_buttons:
                        if button.is_clicked(event.pos):
                            button.action() 
                            break 
        
        elif game_state == "SPELEN":
            pass

        elif game_state == "EINDE":
            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN:
                speler_naam = "" 
                speler_naam_input_active = True
                game_state = "NAAM_INVOER"
                laad_highscores() 

    #update de spelstatus en logica
    if game_state == "SPELEN":
        current_move_command = 0 

        if current_control_mode == CONTROL_MODE_MQTT:
            current_move_command = paddle_mqtt_target_move
        elif current_control_mode == CONTROL_MODE_KEYBOARD:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]:
                current_move_command = -1
            elif keys[pygame.K_DOWN]:
                current_move_command = 1
        
        if current_move_command == -1: 
            if paddle_y > THICKNESS:
                paddle_y -= PADDLE_SPEED
        elif current_move_command == 1: 
            if paddle_y + huidige_paddle_hoogte < GAME_AREA_HEIGHT - THICKNESS:
                paddle_y += PADDLE_SPEED

        
        if paddle_y < THICKNESS: 
            paddle_y = THICKNESS
        if paddle_y + huidige_paddle_hoogte > GAME_AREA_HEIGHT - THICKNESS:
            paddle_y = GAME_AREA_HEIGHT - THICKNESS - huidige_paddle_hoogte

        ball_x += ball_speed_x
        ball_y += ball_speed_y

        if sessie_start_tijd > 0 : 
            totale_speeltijd_sessie = (pygame.time.get_ticks() - sessie_start_tijd) / 1000.0

        
        if ball_y - ball_radius < THICKNESS:
            ball_y = THICKNESS + ball_radius
            ball_speed_y = -ball_speed_y
        if ball_y + ball_radius > GAME_AREA_HEIGHT - THICKNESS:
            ball_y = GAME_AREA_HEIGHT - THICKNESS - ball_radius
            ball_speed_y = -ball_speed_y

        
        if ball_x - ball_radius < THICKNESS:
            ball_x = THICKNESS + ball_radius
            ball_speed_x = -ball_speed_x
            
        
        paddle_rect = pygame.Rect(paddle_x, paddle_y, PADDLE_WIDTH, huidige_paddle_hoogte)
        
        ball_rect = pygame.Rect(ball_x - ball_radius, ball_y - ball_radius, ball_radius * 2, ball_radius * 2)

        if ball_speed_x > 0 and paddle_rect.colliderect(ball_rect): 
            
            ball_x = paddle_x - ball_radius 
            
            bounce_angle_rad = hoek_berekenen_rad(ball_y, paddle_y, huidige_paddle_hoogte)
            
            ball_speed_x = -abs(doel_bal_snelheid * math.cos(bounce_angle_rad)) 
            ball_speed_y = doel_bal_snelheid * math.sin(bounce_angle_rad)
            
            if bounce_sound:
                channel2.play(bounce_sound)
            
        
        if ball_x + ball_radius > GAME_AREA_WIDTH :
            levens -= 1
            if levens == 0:
                voeg_highscore_toe(huidige_level_naam, speler_naam, totale_speeltijd_sessie)
                game_state = "EINDE"
            else:
                reset_bal_voor_nieuwe_beurt() 

    #teken de huidige frame op het scherm
    screen.fill(BLACK) 

    if game_state == "NAAM_INVOER":
        draw_naam_invoer_scherm()
    elif game_state == "MENU_DIFFICULTY":
        draw_moeilijkheid_menu()
    elif game_state == "COUNTDOWN":
        current_time = pygame.time.get_ticks()
        time_left_ms = countdown_end_time - current_time

        if time_left_ms <= 0:
            game_state = "SPELEN"
            sessie_start_tijd = pygame.time.get_ticks() 
            launch_ball() 
            
        else:
            draw_speelveld() 
            draw_info_paneel() 

            countdown_number_display = math.ceil(time_left_ms / 1000.0)
            countdown_text_surf = font_countdown.render(str(int(countdown_number_display)), True, WHITE)
            
            game_area_center_x = GAME_AREA_WIDTH // 2
            game_area_center_y = GAME_AREA_HEIGHT // 2
            countdown_text_rect = countdown_text_surf.get_rect(center=(game_area_center_x, game_area_center_y))
            screen.blit(countdown_text_surf, countdown_text_rect)

    elif game_state == "SPELEN":
        draw_speelveld()
        draw_info_paneel()
    elif game_state == "EINDE":
        draw_sessie_einde_scherm() 
        draw_info_paneel()         

    pygame.display.flip()
    clock.tick(60)

#afsluiten en opruimen
if mqtt_client_instance:
    print("Stopping MQTT client...")
    mqtt_client_instance.loop_stop()
    mqtt_client_instance.disconnect()
    print("MQTT client stopped.")

if channel1: channel1.stop()
pygame.mixer.quit()
pygame.quit()
sys.exit()