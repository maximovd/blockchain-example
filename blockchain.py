# /usr/bin/python

import hashlib
import json
from time import time
from http import HTTPStatus
from abc import ABC, abstractmethod
from urllib.parse import urlparse

import requests


class AbstractBlockchain(ABC):
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()
        # Create the genesis block

    @abstractmethod
    def new_block(self, proof, previous_hash=None):
        """Creates a new Block and adds it to the chain."""
        pass

    @abstractmethod
    def new_transaction(self, sender, recipient, amount):
        """Adds a new transaction to the list of transactions."""
        pass

    @abstractmethod
    def register_node(self, address):
        """
        Add a new node to the list of nodes

        :param address: <str> Address of node. Eg. 'https://192.168.0.5:5000'
        :return: None
        """
        pass

    @abstractmethod
    def valid_chain(self, chain: list) -> bool:
        """
        Determine if a given blockchain is valid.

        :param chain: A blockchain
        :return: True if valid, False if not
        """
        pass

    @abstractmethod
    def resolve_conflicts(self) -> bool:
        """
        This is our Consensus Algorithm, it resolves conflicts by replacing our chain
        with the longest one in the network.

        :return: True if our chain was replaced, False if not
        """
        pass

    @staticmethod
    @abstractmethod
    def hash(block):
        """Hashes a Block"""
        pass

    @property
    @abstractmethod
    def last_block(self):
        """Returns the last Block in the chain."""
        pass


class Blockchain(AbstractBlockchain):
    def __init__(self):
        super().__init__()
        self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof, previous_hash=None):
        """Creates a new Block and adds it to the chain."""
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }
        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """Adds a new transaction to the list of transactions."""
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })
        return self.last_block['index'] + 1

    def register_node(self, address):
        """
        Add a new node to the list of nodes

        :param address: <str> Address of node. Eg. 'https://192.168.0.5:5000'
        :return: None
        """
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain: list) -> bool:
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print('\n---------\n')
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(block):
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1
            return True

    def resolve_conflicts(self) -> bool:
        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'https://{node}/chain')

            if response.status_code == HTTPStatus.OK:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True
        return False


    @staticmethod
    def hash(block):
        """
        Hashes the Block.

        :param block:
        :return:
        """
        # We must make sure that the Dictionary is Ordered, or we'll have
        # inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        """Returns the last Block in the chain."""
        return self.chain[-1]

    def proof_of_work(self, last_proof: int) -> int:
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes,
             where p is previous p'
         - p is the previous proof, and p' is the new proof

        :param last_proof: last proof we know
        :return: proof
        """
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof: int, proof: int) -> bool:
        """
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes ?

        :param last_proof: Previous Proof
        :param proof: Current Proof 
        :return: True if correct, else False
        """
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'
