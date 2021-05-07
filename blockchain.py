# /usr/bin/python

import hashlib
import json
from http import HTTPStatus
from time import time
from abc import ABC, abstractmethod
from uuid import uuid4
from urllib.parse import urlparse

from flask import Flask, jsonify, request


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
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    @staticmethod
    def hash(block):
        """Hashes a Block"""
        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        """Returns the last Block in the chain."""
        return self.chain[-1]

    def proof_of_work(self, last_proof: int) -> int:
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is previous p'
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


# Instantiate our Node
app = Flask(__name__)

#  Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin
    blockchain.new_transaction(
        sender='0',
        recipient=node_identifier,
        amount=1,
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': 'New Block Forged',
        'index': block['index'],
        'transaction': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), HTTPStatus.OK


@app.route('/transactions/new', methods=['POST'])
def new_transactions():
    values = request.get_json()

    # Check that the required fields are in the posted data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', HTTPStatus.BAD_REQUEST

    # Create new Transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), HTTPStatus.CREATED


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), HTTPStatus.OK


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
