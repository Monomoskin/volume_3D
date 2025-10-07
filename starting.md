# inicialize python enviroment setup

python3 -m venv venv

# activate it

source venv/bin/activate

# install prerequisites.txt

Step 2 :

# create account on https://app.cvat.ai

then create project and task
generate annotations

# Configurar el Entorno

Primero, necesitas las librerías adecuadas en tu proyecto.

PyTorch: Es la base de Detectron2. Instala la versión compatible con tu sistema operativo y procesador desde la página oficial de PyTorch.

Detectron2: Una vez que PyTorch esté instalado, puedes instalar Detectron2 con pip.

pip install 'git+https://github.com/facebookresearch/detectron2.git'

# Puedes encontrar un error que te diga que no tienes pytorch instalado:

1. pip install wheel
2. pip3 install torch torchvision torchaudio (for mac users)
3. pip install 'git+https://github.com/facebookresearch/detectron2.git'
