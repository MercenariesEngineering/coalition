cd ../../server
echo $PWD
docker build --no-cache -t coalition:1.0.0alpha -f ../docker/Dockerfile .
