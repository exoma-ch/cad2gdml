\podman run -it \
  --name guimesh-container-3 \
  -v /home/icortino/irene_playground/CADtoGeant4:/mnt/guimesh \
  -v "$SSH_AUTH_SOCK:/tmp/ssh-agent" \
  -e SSH_AUTH_SOCK=/tmp/ssh-agent \
  -v "$HOME/.ssh/known_hosts:/root/.ssh/known_hosts:ro" \
  cad2geant
