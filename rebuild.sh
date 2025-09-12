#!/bin/bash
echo "Stopping containers..."
docker compose down

echo "Building and starting containers..."
docker compose up -d --build

echo "Showing logs..."
docker compose logs -f
