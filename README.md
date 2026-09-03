# D&D App

A simple app for organizing and managing your Dungeons & Dragons adventures.

## Features

- Currently, just a character sheet manager

## Getting Started

Download the app from your mobile devices relevant appstore
(Currently only developing for android/the google playstore)

## Development

The project does not yet support the local phone client, app development will follow server development.

## Design Structure

### Server

The server is largely written in python centered around a core SQLite database. Clients interact with a cache
that is pulled from this database. This database acts as the source of truth for all core D&D information that
the clients may need. Eventually it will lso store user data that allows for cross-device account usage.

### Client

The client represents the physical phone apps pulling information from the server.

## Roadmap

### V1
- Working basic information versioning and cache system on the server side alongside the http data transfer system to interact with the client.
- Simple but working client that effectively will act as a glorified character sheet.