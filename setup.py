from distutils.core import setup

setup(
    name='django-redisession',
    version='0.3.1',
    license='MIT',
    author='Li Meng',
    author_email='liokmkoil@gmail.com',
    packages=['redisession', 'redisession.management', 'redisession.management.commands'],
    description='A Redis-based Django session engine for django.contrib.sessions.',
    long_description=open('README.rst').read(),
    url='https://github.com/liokm/django-redisession',
    download_url='https://github.com/liokm/django-redisession',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
