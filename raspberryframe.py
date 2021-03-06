#!/usr/bin/env python
import os
import sys
import time
import argparse
import logging
import gobject
import pygame
import sgc
from sgc.locals import *

import display
import providers
import themes
import overlay

# Frame:
#   p = Provider(shuffle=True)
#   handle = p.next()
#   # wait for PhotoInfo(handle) event
#   # wait for PhotoLoaded(handle) event
#
# Provider:
#   init:
#     info_queue.push_front(first_five)
#     info_thread_run()
#
#   next:
#     if info_queue == []:
#       info_thread_run(req)
#     info_queue.push_front(req)
#
#   info_done:
#     event(PhotoInfo(handle))
#     if download_queue == []:
#       download_thread_run(req)
#     download_queue.push_front(req)
#
#     if info_queue != []:
#       info_thread_run(info_queue.pop())
#
#   download_done:
#     event(PhotoDownload(handle)
#     if download_queue != []:
#       download_thread_run(download_queue.pop())

CACHE_PATH = os.path.expanduser("~/.raspberryframe_cache")
CACHE_SIZE_MB = 1024 # Limit cache to 1GB

logger = logging.getLogger("Raspberry Frame")
logger.addHandler(logging.StreamHandler())

class RaspberryFrame(sgc.Simple):
    _can_focus = True

    def __init__(self, surf=None, flags=None, crop_threshold=10, **kwargs):
        sgc.Simple.__init__(self, surf, flags, **kwargs)
        self.crop_threshold = crop_threshold

    def _event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect_abs.collidepoint(event.pos):
                self.on_click()

    def on_click(self):
        pygame.event.post(self._create_event("click"))

    def show_image(self, image):
        image = self._letterbox(image)

        self.image.fill(pygame.Color("BLACK"))
        self.image.blit(image, self._centre_offset(image))

    def _letterbox(self, image):
        width, height = image.get_size()

        width_scale_factor = 1.0 * width / self.image.get_width()
        height_scale_factor = 1.0 * height / self.image.get_height()

        # Use the largest scale factor, to prevent cropping
        scale_factor = max(width_scale_factor, height_scale_factor)

        # If the difference in aspect ratios is less than aspect_error,
        # crop the image instead of letterboxing
        aspect_error = abs((width_scale_factor - height_scale_factor) /
                           max(width_scale_factor, height_scale_factor))
        if aspect_error <= self.crop_threshold / 100.0:
            scale_factor = min(width_scale_factor, height_scale_factor)

        new_width = int(width / scale_factor)
        new_height = int(height / scale_factor)

        return pygame.transform.scale(image, (int(width / scale_factor),
                                              int(height / scale_factor)))

    def _centre_offset(self, image):
        width, height = image.get_size()
        return ((self.image.get_width() / 2 - width / 2),
                (self.image.get_height() / 2 - height / 2))

############################################################

class Main:
    def __init__(self, slide_seconds, width=None, height=None, crop_threshold=10, shuffle=True):
        self.screen, self.width, self.height = display.init(width, height)

        self.provider = providers.Provider(self.width, self.height, CACHE_PATH, CACHE_SIZE_MB, shuffle=shuffle)
        self.theme = themes.Theme(self.width, self.height)

        self.frame = RaspberryFrame((self.width, self.height), crop_threshold)
        self.frame.add(fade=False)

        self.clock = pygame.time.Clock()
        self.slide_seconds = slide_seconds
        self.timer = None

        self.overlay = overlay.Overlay(self.theme)

    def run(self):
        gobject.idle_add(self.pygame_loop_cb)
        self.slideshow_next_cb()
        self.start_slideshow()
        gobject.MainLoop().run()

    def start_slideshow(self):
        self.timer = gobject.timeout_add(self.slide_seconds*1000, self.slideshow_next_cb)

    def stop_slideshow(self):
        if self.timer:
            gobject.source_remove(self.timer)
        self.timer = None

    def show_image(self, image):
        """Show an image and restart the slideshow timer"""
        self.frame.show_image(image)
        if self.timer:
            self.stop_slideshow()
            self.start_slideshow()

    def update_overlay(self):
        description = self.provider.get_description(self.photo_object)
        tags = self.provider.get_tags(self.photo_object)
        self.overlay.set_description(description)
        self.overlay.set_tags(tags)
        self.overlay.set_star(self.provider.STAR_TAG in tags)
        self.overlay.set_remove(self.provider.REMOVE_TAG in tags)

    def toggle_star(self):
        tags = self.provider.get_tags(self.photo_object)
        if self.provider.STAR_TAG in tags:
            logger.debug("Removing star...")
            self.provider.remove_tag(self.photo_object, self.provider.STAR_TAG)
        else:
            logger.debug("Adding star...")
            self.provider.add_tag(self.photo_object, self.provider.STAR_TAG)
        self.update_overlay()

    def toggle_remove(self):
        tags = self.provider.get_tags(self.photo_object)
        if self.provider.REMOVE_TAG in tags:
            logger.debug("Unremoving photo...")
            self.provider.remove_tag(self.photo_object, self.provider.REMOVE_TAG)
        else:
            logger.debug("Removing photo...")
            self.provider.add_tag(self.photo_object, self.provider.REMOVE_TAG)
        self.update_overlay()

    def slideshow_next_cb(self):
        self.provider.next_photo(+1)
        return False

    def pygame_loop_cb(self):
        time = self.clock.tick(30)
        sgc.update(time)
        pygame.display.flip()

        for event in pygame.event.get():
            sgc.event(event)

            if event.type == pygame.QUIT:
                sys.exit()

            elif event.type == self.provider.PROVIDER_EVENT:
                if event.name == "photo":
                    self.show_image(event.image)
                    self.photo_object = event.photo_object
                    self.update_overlay()
                    logger.debug(self.photo_object)

                elif event.name == "error":
                    logger.error("Could not display photo: %s" % event.error)
                    if self.timer:
                        self.stop_slideshow()
                        self.start_slideshow()

            elif event.type == GUI:
                if event.widget == self.frame:
                    if self.overlay.active():
                        self.overlay.remove()
                        self.start_slideshow()
                    else:
                        self.stop_slideshow()
                        self.overlay.add()
                if event.widget == self.overlay.star_button:
                    self.toggle_star()
                if event.widget == self.overlay.remove_button:
                    self.toggle_remove()
                elif event.widget == self.overlay.back_button:
                    self.provider.next_photo(-1)
                elif event.widget == self.overlay.forward_button:
                    self.provider.next_photo(+1)

        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plays a Trovebox slideshow to a framebuffer.")
    parser.add_argument("-t", "--slide_seconds", type=int, default=30,
                        help="Delay between slides in seconds (default:30)")
    parser.add_argument("-s", "--size", default=None,
                        help="Target photo size (default:screen resolution)")
    parser.add_argument("-c", "--crop_threshold", type=int, default=10,
                        help="Crop the photo if the photo/screen aspect ratios are within this percentage")
    parser.add_argument("-n", "--no-shuffle", action="store_true",
                        help="Disable shuffle")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Print additional debug information")
    options = parser.parse_args()

    if options.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    width = None
    height = None
    if options.size:
        try:
            width, height = options.size.split("x")
            width, height = int(width), int(height)
        except ValueError:
            parser.error("Please specify photo size as 'widthxheight'\n(eg: -r 1920x1080)")

    Main(slide_seconds=options.slide_seconds,
         width=width, height=height,
         crop_threshold=options.crop_threshold,
         shuffle=(not options.no_shuffle)).run()


