import logging
import os

from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils.http import urlencode
from linebot.models import RichMenu, RichMenuBounds, RichMenuArea, URIAction, PostbackAction, RichMenuSize
from django.db import models

from settings import STATICFILES_DIRS, HOSTNAME


(MAIN_MENU, ) = range(1)
RICH_MENU_INDEX_CHOICES = [
    (MAIN_MENU, 'main menu'),
]

class LineRichMenu(models.Model):
    line_channel_membership = models.ForeignKey('line_app.LineChannelMembership', on_delete=models.CASCADE, related_name='line_rich_menus')

    index = models.SmallIntegerField(choices=RICH_MENU_INDEX_CHOICES, default=MAIN_MENU)
    _is_currently_active = models.BooleanField(default=False)
    line_rich_menu_id = models.CharField(max_length=50, null=True)

    # MODEL PROPERTIES

    @property
    def line_channel(self):
        return self.line_channel_membership.line_channel

    @property
    def shop(self):
        return self.line_channel_membership.line_channel.shop

    @property
    def is_currently_active(self) -> bool:
        return bool(self._is_currently_active)

    # MODEL FUNCTIONS

    def get_menu(self, index=MAIN_MENU):

        login_kwargs = {'eid': self.line_channel_membership.url_safe_uuid}

        return RichMenu(
            size=RichMenuSize(width=1000, height=315),
            selected=True,
            name="Menu",
            chat_bar_text="Start",
            areas=[
                RichMenuArea(
                    bounds=RichMenuBounds(x=15, y=8, width=300, height=300),
                    action=PostbackAction(label='Call', data='action=place_call')
                    # action=URIAction(label='Call', uri=f'tel:{self.line_channel.shop.contact_phone_number}')
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=300+33+15, y=8, width=300, height=300),
                    action=URIAction(
                        label='Order',
                        uri=f'https://{HOSTNAME}{self.shop.menu.get_absolute_url()}?{urlencode(login_kwargs)}'
                    )
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=600 + 67 + 15, y=8, width=300, height=300),
                    action=URIAction(
                        label='Preferences',
                        uri=f'https://{HOSTNAME}{self.shop.get_absolute_url()}?{urlencode(login_kwargs)}'
                    )
                ),
            ]
        )


    def publish_and_save(self, force_refresh=False):
        if self.line_rich_menu_id and not force_refresh:
            return self.line_rich_menu_id

        line_channel_bot = self.line_channel.get_bot()

        if self.line_rich_menu_id and force_refresh:
            line_channel_bot.delete_rich_menu(self.line_rich_menu_id)

        self.line_rich_menu_id = line_channel_bot.api.create_rich_menu(rich_menu=self.get_menu())
        logging.debug(f"rich_menu_id: {self.line_rich_menu_id}")

        # upload image and link it to rich_menu
        # from https://developers.line.biz/en/reference/messaging-api/#upload-rich-menu-image
        with open(os.path.join(STATICFILES_DIRS[0], 'image/menu-circle-buttons.png'), 'rb') as f:
            line_channel_bot.api.set_rich_menu_image(self.line_rich_menu_id, 'image/png', f)

        self.save()
        return self.line_rich_menu_id


    def assign_to_user(self):
        if not self.line_rich_menu_id:
            raise Exception("rich menu must be published before it can be assigned to a user")

        line_channel_bot = self.line_channel.get_bot()
        line_channel_bot.api.link_rich_menu_to_user(
            self.line_channel_membership.line_user_profile.line_user_id,
            self.line_rich_menu_id
        )
        self.set_currently_active()


    # def assign_to_users(self, user_queryset):
    #     line_channel_bot = self.line_channel.get_bot()
    #     if not self.line_rich_menu_id:
    #         self.publish()
    #
    #     line_channel_bot.api.link_rich_menu_to_users(
    #         [user.line_user_profile.line_user_id for user in user_queryset],
    #         self.line_rich_menu_id
    #     )

    def set_currently_active(self):
        for lrm in LineRichMenu.objects.filter(
                line_channel_membership=self.line_channel_membership,
                _is_currently_active=True
        ):
            lrm._is_currently_active = False
            lrm.save()
        self._is_currently_active = True
        self.save()

    class Meta:
        ordering = ('index',)
        # unique_together = ('line_channel_membership', 'index')


@receiver(pre_delete, sender=LineRichMenu)
def delete_richmenu(sender, instance, **kwargs):
    line_channel_bot = instance.line_channel.get_bot()
    from linebot.exceptions import LineBotApiError
    try:
        line_channel_bot.api.delete_rich_menu(instance.line_rich_menu_id)
    except LineBotApiError:
        pass
