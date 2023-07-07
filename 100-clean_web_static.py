#!/usr/bin/python3
'''module:
deploy web static to web servers
'''

from fabric.api import env, local, put, run, lcd, cd
from os.path import exists, isfile
import os
import argparse
from datetime import datetime

env.hosts = ['100.26.133.229', '54.152.176.94']


def do_pack():
    '''function:
    generates a .tgz archive from the contents of the web_static folder
    '''
    now = datetime.utcnow().strftime('%Y%m%d%H%M%S')

    artifact = f'versions/web_static_{now}.tgz'
    print(f'Packing web_static to {artifact}')
    if not os.path.exists('versions'):
        os.makedirs('versions')

    fab_stat = local(f'tar -cvzf {artifact} web_static')
    if fab_stat.succeeded:
        size = os.path.getsize(artifact)
        print(f'web_static packed: {artifact} -> {size}Bytes')
        return artifact
    else:
        return None


def do_deploy(archive_path):
    '''function:
    distributes an archive to your web servers
    '''

    if not exists(archive_path) and not isfile(archive_path):
        return False

    try:
        archive_filename = os.path.basename(archive_path)
        no_ext = os.path.splitext(archive_filename)[0]

        # upload the archive to the /tmp/ directory of the web server:
        put(archive_path, '/tmp/')

        # unarchive - uncompress the archive to the folder:
        release_folder = '/data/web_static/releases/' + no_ext + '/'
        run('mkdir -p {}'.format(release_folder))
        run('tar -xzf /tmp/{} -C {}'.format(archive_filename, release_folder))

        # delete the archive from the web server
        # move files to proper locations:
        run('rm /tmp/{}'.format(archive_filename))
        run('mv {}web_static/* {}'.format(release_folder, release_folder))

        run('rm -f /data/web_static/current')
        run('ln -s {} /data/web_static/current'.format(release_folder))

        print('New version deployed!')
        return True

    except Exception:
        return False


def deploy():
    '''function:
    creates and distributes an archive to your web servers
    '''

    # call the do_pack() function and store the path of the created archive
    archive_path = do_pack()

    # Return False if no archive has been created
    if archive_path is None:
        return False

    # call the do_deploy(archive_path) function,
    # using the new path of the new archive
    return do_deploy(archive_path)


def do_clean(number=0):
    '''function:
    deletes out-of-date archives
    '''

    number = int(number)
    if number < 0:
        return False
    elif number == 0 or number == 1:
        number_to_keep = 1
    else:
        number_to_keep = number

    # delete unnecessary archives in the versions folder
    with lcd('versions'):
        local('ls -1t | tail -n +{} | xargs rm -rf'.format(number_to_keep + 1))

    # delete unnecessary archives in the /data/web_static/releases folder
    with cd('/data/web_static/releases'):
        run('ls -1t | tail -n +{} | xargs rm -rf'.format(number_to_keep + 1))

    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username', type=str,
                        help='SSH username')
    parser.add_argument('-i', '--private-key', type=str,
                        help='Path to SSH private key')
    parser.add_argument('--number', type=int, default=0,
                        help='Number of archives to keep')
    args = parser.parse_args()

    if args.username:
        env.user = args.username

    if args.private_key:
        env.key_filename = args.private_key

    do_clean(args.number)
