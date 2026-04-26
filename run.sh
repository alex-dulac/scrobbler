#!/bin/bash
set -e

if [ ! -d "venv" ]; then
    echo "Virtual environment not found."
    read -p "Would you like to create and install it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Creating virtual environment..."
        python -m venv venv
        source venv/bin/activate

        echo "Installing dependencies..."
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    else
        echo "Exiting."
        exit 1
    fi
else
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

echo "Starting textual app..."
python textual_app.py
