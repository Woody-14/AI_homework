import requests
from fastapi import FastAPI
import fastapi
from pydantic import BaseModel
import uvicorn
import os
import signal
import logging

"""
By Todd Dole, Revision 1.2
Written for Hardin-Simmons CSCI-4332 Artificial Intelligence
Revision History
1.0 - API setup
1.1 - Very basic test player
1.2 - Bugs fixed and player improved, should no longer forfeit
"""

# Configuration
DEBUG = True
PORT = 11300
USER_NAME = "jw2107"

# Global state variables
hand = []  # list of cards in our hand
discard = []  # list of cards organized as a stack
cannot_discard = ""

# Initialize FastAPI app
app = FastAPI()


@app.get("/")
async def root():
    '''Root API simply confirms API is up and running.'''
    return {"status": "Running"}


class GameInfo(BaseModel):
    game_id: str
    opponent: str
    hand: str


@app.post("/start-2p-game/")
async def start_game(game_info: GameInfo):
    '''Game Server calls this endpoint to inform player a new game is starting.'''
    global hand, discard
    hand = game_info.hand.split()
    hand.sort()
    discard = []
    logging.info(f"2p game started, hand is {hand}")
    return {"status": "OK"}


class HandInfo(BaseModel):
    hand: str


@app.post("/start-2p-hand/")
async def start_hand(hand_info: HandInfo):
    '''Game Server calls this endpoint to inform player a new hand is starting.'''
    global hand, discard
    hand = hand_info.hand.split()
    hand.sort()
    discard = []
    logging.info(f"2p hand started, hand is {hand}")
    return {"status": "OK"}


def process_events(event_text):
    '''Process game events and update state.'''
    global hand, discard, cannot_discard

    for event_line in event_text.strip().splitlines():
        if (USER_NAME + " draws") in event_line or (USER_NAME + " takes") in event_line:
            card = event_line.split()[-1]
            hand.append(card)
            hand.sort()
            logging.info(f"Drew {card}, hand is now: {hand}")

        elif "discards" in event_line:
            card = event_line.split()[-1]
            discard.insert(0, card)

        elif "takes" in event_line and USER_NAME not in event_line:
            if discard:
                discard.pop(0)

        elif " Ends:" in event_line:
            logging.info(event_line)


class UpdateInfo(BaseModel):
    game_id: str
    event: str


@app.post("/update-2p-game/")
async def update_2p_game(update_info: UpdateInfo):
    process_events(update_info.event)
    logging.info(f"Update received: {update_info.event}")
    return {"status": "OK"}


@app.post("/draw/")
async def draw(update_info: UpdateInfo):
    '''Handle draw decision.'''
    global cannot_discard
    process_events(update_info.event)

    if not discard:
        cannot_discard = ""
        return {"play": "draw stock"}

    # Check if we have any cards matching the top discard card's rank
    top_card = discard[0]
    if any(card[0] == top_card[0] for card in hand):
        cannot_discard = top_card
        return {"play": "draw discard"}

    return {"play": "draw stock"}


def find_sets(cards):
    '''Find all sets of three or more cards of the same rank.'''
    rank_counts = {}
    for card in cards:
        rank = card[0]
        rank_counts[rank] = rank_counts.get(rank, []) + [card]
    return [cards for cards in rank_counts.values() if len(cards) >= 3]


def find_runs(cards):
    '''Find all runs of three or more consecutive cards of the same suit.'''
    suit_cards = {}
    for card in cards:
        suit = card[1]
        suit_cards[suit] = suit_cards.get(suit, []) + [card]

    runs = []
    ranks = "23456789TJQKA"
    for suit_group in suit_cards.values():
        suit_group.sort(key=lambda x: ranks.index(x[0]))
        current_run = [suit_group[0]]

        for card in suit_group[1:]:
            if ranks.index(card[0]) == ranks.index(current_run[-1][0]) + 1:
                current_run.append(card)
            else:
                if len(current_run) >= 3:
                    runs.append(current_run[:])
                current_run = [card]

        if len(current_run) >= 3:
            runs.append(current_run)

    return runs


@app.post("/lay-down/")
async def lay_down(update_info: UpdateInfo):
    '''Handle melding and discard decisions.'''
    global hand, cannot_discard
    process_events(update_info.event)

    play_actions = []
    hand_copy = hand.copy()

    # Find and play sets
    sets = find_sets(hand_copy)
    for set_cards in sets:
        if len(set_cards) >= 3:
            meld = set_cards[:3]  # Take exactly 3 cards
            play_actions.append(f"meld {' '.join(meld)}")
            for card in meld:
                hand_copy.remove(card)

    # Find and play runs
    runs = find_runs(hand_copy)
    for run in runs:
        if len(run) >= 3:
            play_actions.append(f"meld {' '.join(run)}")
            for card in run:
                if card in hand_copy:
                    hand_copy.remove(card)

    # Must discard one card
    if hand_copy:
        # Try to discard a card that's not part of any potential meld
        discard_card = None
        for card in reversed(hand_copy):
            if card != cannot_discard:
                discard_card = card
                break

        if not discard_card and hand_copy:
            discard_card = hand_copy[0]

        if discard_card:
            play_actions.append(f"discard {discard_card}")
            hand_copy.remove(discard_card)

    # Update the actual hand
    hand = hand_copy

    play_string = ' '.join(play_actions)
    if not play_string and hand:
        # If no actions were taken but we have cards, we must discard
        return {"play": f"discard {hand[0]}"}

    logging.info(f"Playing: {play_string}")
    return {"play": play_string}


@app.get("/shutdown")
async def shutdown_API():
    '''Shutdown the API (debug mode only).'''
    os.kill(os.getpid(), signal.SIGTERM)
    logging.info("Player client shutting down...")
    return fastapi.Response(status_code=200, content='Server shutting down...')


if __name__ == "__main__":
    if DEBUG:
        url = "http://127.0.0.1:16200/test"
        logging.basicConfig(
            filename="RummyPlayer.log",
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            level=logging.INFO
        )
    else:
        url = "http://127.0.0.1:16200/register"
        logging.basicConfig(
            filename="RummyPlayer.log",
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            level=logging.WARNING
        )

    payload = {
        "name": USER_NAME,
        "address": "127.0.0.1",
        "port": str(PORT)
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Request succeeded.")
            print("Response:", response.json())
            uvicorn.run(app, host="127.0.0.1", port=PORT)
        else:
            print("Request failed with status:", response.status_code)
            print("Response:", response.text)
            exit(1)
    except Exception as e:
        print("Failed to connect to server. Please contact Mr. Dole.")
        exit(1)