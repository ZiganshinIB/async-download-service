import os
from aiohttp import web
import asyncio
import aiofiles
import argparse
from sys import stdout
import datetime
import logging


INTERVAL_SECS = 1


async def handler_archive(request):
    archive_hash = request.match_info['archive_hash']
    path_files = os.path.join(args.loading_path, archive_hash)
    if not os.path.exists(path_files):
        return web.HTTPNotFound(text=f'Архив {archive_hash} не существует или был удален')
    load_process = await asyncio.create_subprocess_exec(
        'zip',
        '-r',
        '-', '.',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=path_files
    )
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'txt/html'
    response.headers['Content-Disposition'] = f'attachment; filename="photos.zip"'

    await response.prepare(request)
    try:
        while not load_process.stdout.at_eof():
            chunk = await load_process.stdout.read(n=200*(2**10))
            logging.info(f'Sending archive chunk ...')
            await response.write(chunk)
            if args.delay:
                await asyncio.sleep(args.delay)
    except asyncio.CancelledError as e:
        logging.warning(f'Download was interrupted')
        raise
    finally:
        load_process.kill()
        await load_process.communicate()
    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r', encoding='utf-8') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--loading_path', '-p', default='test_photos', help='Путь к папке с архивами')
    parser.add_argument('--logging', '-l', action='store_true', help='Включает логирование')
    parser.add_argument('--delay', '-d', type=int, default=1, help='Задержка в секундах между скачиваниями')
    args = parser.parse_args()
    if args.logging:
        logging.basicConfig(
            format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
            level=logging.INFO
        )
    INTERVAL_SECS = args.delay
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page, ),
        web.get('/archive/{archive_hash}/', handler_archive),

    ])
    web.run_app(app)
