from setuptools import setup

setup(name='portadaMicroservices',
    version='0.1',
    description='microservices for PortADa project',
    author='PortADa team',
    author_email='jcbportada@gmail.com',
    license='MIT',
    url="https://github.com/portada-git/py_portada_microservices",
    packages=['portada_microservices.services', 'portada_microservices.client'],
    install_requires=[
	imageio[pyav],
	imageio[opencv],
	flask~=3.0.2
	requests~=2.31.0
	pyjwt
	flask-reuploads
	py_portada_image @ git+https://github.com/portada-git/py_portada_image#egg=py_portada_image,
	werkzeug~=3.0.1
    ],
    python_requires='>=3.9',
    zip_safe=False)
