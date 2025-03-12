from setuptools import setup

setup(name='portadaMicroservices',
    version='0.1.30',
    description='microservices for PortADa project',
    author='PortADa team',
    author_email='jcbportada@gmail.com',
    license='MIT',
    url="https://github.com/portada-git/py_portada_microservices",
    packages=['portada_microservices.services', 'portada_microservices.client'],
    install_requires=[
	'flask',
	'requests',
	'pyjwt',
	'flask-reuploads',
	'py_portada_image @ git+https://github.com/portada-git/py_portada_image#egg=py_portada_image',
	'werkzeug',
	'configparser',
    'py_portada_order_blocks @ git+https://github.com/portada-git/py_order_text_blocks#egg=py_portada_order_blocks',
    'cryptography',
    'py_portada_paragraphs @ git+https://github.com/portada-git/py_portada_paragraphs#egg=py_portada_paragraphs',
    'py_openai_extractor @ git+https://github.com/portada-git/py_portada_openai_extractor#egg=py_openai_extractor'
    ],
    python_requires='>=3.9',
    zip_safe=False)
