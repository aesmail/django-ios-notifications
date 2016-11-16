# -*- coding: utf-8 -*-

from optparse import make_option
import json
import sys

from django.core.management.base import BaseCommand, CommandError

from ios_notifications.models import Notification, APNService


class Command(BaseCommand):
    help = 'Create and immediately send a push notification to iOS devices'
    def add_arguments(self, parser):
        parser.add_argument('--message',
            help='The main message to be sent in the notification',
            action='store',
            dest='message',
            default='')
        
        parser.add_argument('--badge',
            help='The badge number of the notification',
            action='store',
            dest='badge',
            default=None)
        
        parser.add_argument('--sound',
            help='The sound for the notification',
            action='store',
            dest='sound',
            default='')
        
        parser.add_argument('--service',
            help='The id of the APN Service to send this notification through',
            action='store',
            dest='service',
            default=None)
        
        parser.add_argument('--extra',
            help='Custom notification payload values as a JSON dictionary',
            action='store',
            dest='extra',
            default=None)
        
        parser.add_argument('--persist',
                    help='Save the notification in the database after pushing it.',
                    action='store_true',
                    dest='persist',
                    default=None)
        
        parser.add_argument('--no-persist',
                    help='Prevent saving the notification in the database after pushing it.',
                    action='store_false',
                    dest='persist')  # Note: same dest as --persist; they are mutually exclusive
        
        parser.add_argument('--batch-size',
                    help='Notifications are sent to devices in batches via the APN Service. This controls the batch size. Default is 100.',
                    action='store',
                    dest='chunk_size',
                    default=100)

    def handle(self, *args, **options):
        if options['service'] is None:
            raise CommandError('The --service option is required')
        try:
            service_id = int(options['service'])
        except ValueError:
            raise CommandError('The --service option should pass an id in integer format as its value')
        if options['badge'] is not None:
            try:
                options['badge'] = int(options['badge'])
            except ValueError:
                raise CommandError('The --badge option should pass an integer as its value')
        try:
            service = APNService.objects.get(pk=service_id)
        except APNService.DoesNotExist:
            raise CommandError('APNService with id %d does not exist' % service_id)

        message = options['message']
        extra = options['extra']

        if not message and not extra:
            raise CommandError('To send a notification you must provide either the --message or --extra option.')

        notification = Notification(message=options['message'],
                                    badge=options['badge'],
                                    service=service,
                                    sound=options['sound'])

        if options['persist'] is not None:
            notification.persist = options['persist']

        if extra is not None:
            notification.extra = json.loads(extra)

        try:
            chunk_size = int(options['chunk_size'])
        except ValueError:
            raise CommandError('The --batch-size option should be an integer value.')

        if not notification.is_valid_length():
            raise CommandError('Notification exceeds the maximum payload length. Try making your message shorter.')

        service.push_notification_to_devices(notification, chunk_size=chunk_size)
        if 'test' not in sys.argv:
            self.stdout.write('Notification pushed successfully\n')
