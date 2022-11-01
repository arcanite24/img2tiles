import math

import modules.scripts as scripts
import gradio as gr
from PIL import Image

from modules import processing, images, devices
from modules.processing import Processed
from modules.shared import state


class Script(scripts.Script):
    def title(self):
        return "img2tiles"

    def show(self, is_img2img):
        return is_img2img

    def ui(self, is_img2img):
        tile_size = gr.Slider(minimum=32, maximum=256, step=16,
                              label='Tile size', value=256, visible=True)

        overlap = gr.Slider(minimum=0, maximum=256, step=16,
                            label='Tile overlap', value=0, visible=True)

        increment_seed = gr.Checkbox(label='New seed for each tile', value=True, visible=True)

        return [tile_size, overlap, increment_seed]

    def run(self, p, tile_size, overlap, increment_seed):
        processing.fix_seed(p)

        initial_info = None
        seed = p.seed
        

        init_img = p.init_images[0]
        img = init_img

        devices.torch_gc()

        batch_size = p.batch_size

        grid = images.split_grid(
            img, tile_w=tile_size, tile_h=tile_size, overlap=overlap)

        work = []

        for y, h, row in grid.tiles:
            for tiledata in row:
                work.append(tiledata[2])
                # tiledata[2].show()

        batch_count = math.ceil(len(work) / batch_size)
        state.job_count = batch_count

        print(
            f"img2tiles will process a total of {len(work)} images tiled as {len(grid.tiles[0][2])}x{len(grid.tiles)} in a total of {state.job_count} batches.")

        result_images = []
        work_results = []

        for i in range(batch_count):
            p.batch_size = batch_size
            p.init_images = work[i*batch_size:(i+1)*batch_size]

            state.job = f"Batch {i + 1 * batch_count} out of {state.job_count}"
            if increment_seed is True:
                p.seed = p.seed + 1

            processed = processing.process_images(p)

            if initial_info is None:
                initial_info = processed.info

            work_results += processed.images if batch_size == 1 else processed.images[1:]

        shape = (len(grid.tiles[0][2]), len(grid.tiles))
        image_size = (p.width * shape[1], p.height * shape[0])
        combined_image = Image.new('RGB', image_size)

        for row in range(shape[0]):
            for col in range(shape[1]):
                offset = p.width * col, p.height * row
                idx = row * shape[1] + col
                combined_image.paste(work_results[idx], offset)

        result_images.append(combined_image)

        processed = Processed(p, result_images, seed, initial_info)

        return processed
