# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Alias',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('name', models.CharField(verbose_name='Alias', max_length=100)),
            ],
            options={
                'verbose_name_plural': 'aliases',
                'db_table': 'alias',
            },
        ),
        migrations.CreateModel(
            name='APIKey',
            fields=[
                ('key', models.CharField(db_index=True, max_length=20, verbose_name='Key', primary_key=True, serialize=False)),
                ('date_opened', models.DateField(auto_now_add=True, verbose_name='Date opened')),
                ('organization', models.CharField(verbose_name='Name/organization', max_length=200)),
                ('contact', models.CharField(verbose_name='Contact', max_length=200)),
                ('requests', models.IntegerField(verbose_name='Requests')),
            ],
            options={
                'db_table': 'apikey',
            },
        ),
        migrations.CreateModel(
            name='BalanceEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('date', models.DateField(verbose_name='Date')),
                ('pvt_wins', models.IntegerField(verbose_name='PvT wins')),
                ('pvt_losses', models.IntegerField(verbose_name='PvT losses')),
                ('pvz_wins', models.IntegerField(verbose_name='PvZ wins')),
                ('pvz_losses', models.IntegerField(verbose_name='PvZ losses')),
                ('tvz_wins', models.IntegerField(verbose_name='TvZ wins')),
                ('tvz_losses', models.IntegerField(verbose_name='TvZ losses')),
                ('p_gains', models.FloatField(verbose_name='P gains')),
                ('t_gains', models.FloatField(verbose_name='T gains')),
                ('z_gains', models.FloatField(verbose_name='Z gains')),
            ],
            options={
                'db_table': 'balanceentry',
            },
        ),
        migrations.CreateModel(
            name='Earnings',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('earnings', models.IntegerField(null=True, blank=True, verbose_name='Earnings (USD)', help_text='Prize money converted to USD (historically accurate conversion rate)')),
                ('origearnings', models.DecimalField(decimal_places=8, max_digits=20, verbose_name='Earnings (original currency)', help_text='Prize money in original currency')),
                ('currency', models.CharField(max_length=30, verbose_name='Original currency', help_text='Original currency (ISO 4217)')),
                ('placement', models.IntegerField(verbose_name='Place', help_text='Placement')),
            ],
            options={
                'ordering': ['-earnings'],
                'db_table': 'earnings',
            },
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, verbose_name='Name', help_text='Event name')),
                ('lft', models.IntegerField(default=None, blank=True, verbose_name='Left', null=True)),
                ('rgt', models.IntegerField(default=None, blank=True, verbose_name='Right', null=True)),
                ('idx', models.IntegerField(db_index=True, verbose_name='Index', help_text='Canonical sort index')),
                ('closed', models.BooleanField(default=False, db_index=True, verbose_name='Closed')),
                ('big', models.BooleanField(default=False, verbose_name='Big')),
                ('noprint', models.BooleanField(default=False, db_index=True, verbose_name='No print')),
                ('fullname', models.CharField(default='', max_length=500, verbose_name='Full name', help_text='Full event name')),
                ('homepage', models.CharField(null=True, max_length=200, blank=True, verbose_name='Homepage', help_text='Homepage URI')),
                ('lp_name', models.CharField(null=True, max_length=200, blank=True, verbose_name='Liquipedia title', help_text='Liquipedia title')),
                ('tlpd_id', models.IntegerField(null=True, blank=True, verbose_name='TLPD ID', help_text='TLPD id')),
                ('tlpd_db', models.IntegerField(null=True, blank=True, verbose_name='TLPD Databases', help_text='TLPD databases (bit-flag value, 1=WoL KR, 2=WoL intl, 4=HotS, 8=HotS beta, 16=WoL beta)')),
                ('tl_thread', models.IntegerField(null=True, blank=True, verbose_name='Teamliquid.net thread ID', help_text='TL.net thread id')),
                ('prizepool', models.NullBooleanField(db_index=True, verbose_name='Has prize pool', help_text='Has prizepool? True, false or null (unknown)')),
                ('earliest', models.DateField(db_index=True, null=True, blank=True, verbose_name='Earliest match', help_text='Earliest match')),
                ('latest', models.DateField(db_index=True, null=True, blank=True, verbose_name='Latest match', help_text='Latest match')),
                ('category', models.CharField(db_index=True, blank=True, max_length=50, choices=[('individual', 'Individual'), ('team', 'Team'), ('frequent', 'Frequent')], help_text='Category (individual, team or frequent), only for root events', verbose_name='Category', null=True)),
                ('type', models.CharField(db_index=True, max_length=50, choices=[('category', 'Category'), ('event', 'Event'), ('round', 'Round')], help_text='Type (category, event or round)')),
                ('wcs_year', models.IntegerField(choices=[(2013, '2013'), (2014, '2014'), (2015, '2015')], blank=True, verbose_name='WCS year', null=True)),
                ('wcs_tier', models.IntegerField(choices=[(0, 'Native'), (1, 'Tier #1'), (2, 'Tier #2'), (3, 'Tier #3')], blank=True, verbose_name='WCS tier', null=True)),
            ],
            options={
                'ordering': ['idx', 'latest', 'fullname'],
                'db_table': 'event',
            },
        ),
        migrations.CreateModel(
            name='EventAdjacency',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('distance', models.IntegerField(default=None, null=True)),
                ('child', models.ForeignKey(related_name='uplink', to='ratings.Event')),
                ('parent', models.ForeignKey(related_name='downlink', to='ratings.Event')),
            ],
            options={
                'db_table': 'eventadjacency',
            },
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=100, verbose_name='Name', help_text='Team name')),
                ('shortname', models.CharField(null=True, max_length=25, blank=True, verbose_name='Short name', help_text='Short team name')),
                ('scoreak', models.FloatField(default=0.0, null=True, verbose_name='AK score', help_text='All-kill score')),
                ('scorepl', models.FloatField(default=0.0, null=True, verbose_name='PL score', help_text='Proleague score')),
                ('meanrating', models.FloatField(default=0.0, null=True, verbose_name='Rating', help_text='Latest mean rating of top five players')),
                ('founded', models.DateField(null=True, blank=True, verbose_name='Date founded', help_text='Date founded')),
                ('disbanded', models.DateField(null=True, blank=True, verbose_name='Date disbanded', help_text='Date disbanded (if inactive)')),
                ('active', models.BooleanField(default=True, db_index=True, verbose_name='Active', help_text='True if active')),
                ('homepage', models.CharField(null=True, max_length=200, blank=True, verbose_name='Homepage', help_text='Team homepage URI')),
                ('lp_name', models.CharField(null=True, max_length=200, blank=True, verbose_name='Liquipedia title', help_text='Liquipedia title')),
                ('is_team', models.BooleanField(default=True, db_index=True, verbose_name='Team')),
                ('is_manual', models.BooleanField(default=True, verbose_name='Manual entry')),
            ],
            options={
                'db_table': 'group',
            },
        ),
        migrations.CreateModel(
            name='GroupMembership',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('start', models.DateField(blank=True, verbose_name='Date joined', null=True)),
                ('end', models.DateField(blank=True, verbose_name='Date left', null=True)),
                ('current', models.BooleanField(default=True, db_index=True, verbose_name='Current')),
                ('playing', models.BooleanField(default=True, db_index=True, verbose_name='Playing')),
                ('group', models.ForeignKey(to='ratings.Group')),
            ],
            options={
                'db_table': 'groupmembership',
            },
        ),
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('date', models.DateField(verbose_name='Date played', help_text='Date played')),
                ('sca', models.SmallIntegerField(db_index=True, verbose_name='Score for player A', help_text='Score for player A')),
                ('scb', models.SmallIntegerField(db_index=True, verbose_name='Score for player B', help_text='Score for player B')),
                ('rca', models.CharField(db_index=True, max_length=1, choices=[('P', 'Protoss'), ('T', 'Terran'), ('Z', 'Zerg'), ('R', 'Random')], verbose_name='Race A', help_text='Race for player A')),
                ('rcb', models.CharField(db_index=True, max_length=1, choices=[('P', 'Protoss'), ('T', 'Terran'), ('Z', 'Zerg'), ('R', 'Random')], verbose_name='Race B', help_text='Race for player B')),
                ('treated', models.BooleanField(default=False, verbose_name='Computed', help_text='True if the given period has been recomputed since last change')),
                ('event', models.CharField(default='', max_length=200, blank=True, verbose_name='Event text (deprecated)', help_text='Event text (if no event object)')),
                ('game', models.CharField(default='WoL', db_index=True, max_length=10, choices=[('WoL', 'Wings of Liberty'), ('HotS', 'Heart of the Swarm'), ('LotV', 'Legacy of the Void')], help_text='Game version', verbose_name='Game')),
                ('offline', models.BooleanField(default=False, db_index=True, verbose_name='Offline', help_text='True if the match was played offline')),
                ('eventobj', models.ForeignKey(to='ratings.Event', blank=True, help_text='Event object', verbose_name='Event', null=True)),
            ],
            options={
                'verbose_name_plural': 'matches',
                'db_table': 'match',
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('type', models.CharField(choices=[('info', 'info'), ('warning', 'warning'), ('error', 'error'), ('success', 'success')], verbose_name='Type', max_length=10)),
                ('message', models.CharField(default='', choices=[('You might be looking for %(player)s.', 'You might be looking for %(player)s.'), ('You might be looking for %(players)s or %(player)s.', 'You might be looking for %(players)s or %(player)s.'), ('%(player)s recieved a walkover.', '%(player)s recieved a walkover.'), ('%(player)s recieved a walkover against %(opponent)s.', '%(player)s recieved a walkover against %(opponent)s.'), ('%(player)s forfeited.', '%(player)s forfeited.'), ('%(player)s was disqualified.', '%(player)s was disqualified.'), ('%(player)s forfeited and was replaced by %(otherplayer)s.', '%(player)s forfeited and was replaced by %(otherplayer)s.'), ('%(players)s and %(player)s forfeited.', '%(players)s and %(player)s forfeited.'), ('%(player)s forfeited against %(opponent)s.', '%(player)s forfeited against %(opponent)s.'), ('%(player)s forfeited after game %(num)s.', '%(player)s forfeited after game %(num)s.'), ('%(player)s forfeited game %(num)s.', '%(player)s forfeited game %(num)s.'), ('%(player)s forfeited the remaining games.', '%(player)s forfeited the remaining games.'), ('%(player)s forfeited the remaining matches.', '%(player)s forfeited the remaining matches.'), ('%(players)s and %(player)s forfeited the remaining matches.', '%(players)s and %(player)s forfeited the remaining matches.'), ('In addition, %(player)s received a walkover against %(opponent)s.', 'In addition, %(player)s received a walkover against %(opponent)s.'), ('In addition, %(player)s forfeited against %(opponent)s.', 'In addition, %(player)s forfeited against %(opponent)s.'), ('In addition, %(player)s and %(opponent)s played an unrated match.', 'In addition, %(player)s and %(opponent)s played an unrated match.'), ('In addition, %(playera)s and %(playerb)s won a 2v2 against %(playerc)s and %(playerd)s.', 'In addition, %(playera)s and %(playerb)s won a 2v2 against %(playerc)s and %(playerd)s.'), ('%(player)s played %(race)s in game %(num)s.', '%(player)s played %(race)s in game %(num)s.'), ('%(player)s played %(race)s.', '%(player)s played %(race)s.'), ('%(player)s switched to %(race)s after game %(num)s.', '%(player)s switched to %(race)s after game %(num)s.'), ('%(player)s was smurfing for %(otherplayer)s.', '%(player)s was smurfing for %(otherplayer)s.'), ('%(player)s was smurfing as %(otherplayer)s.', '%(player)s was smurfing as %(otherplayer)s.'), ('%(player)s was smurfing as %(otherplayer)s and was disqualified due to residency rules.', '%(player)s was smurfing as %(otherplayer)s and was disqualified due to residency rules.'), ('%(player)s was unable to attend.', '%(player)s was unable to attend.'), ('This match was split due to race-changing.', 'This match was split due to race-changing.'), ("Coming from the loser's bracket, %(player)s had to win two Bo%(num)ss.", "Coming from the loser's bracket, %(player)s had to win two Bo%(num)ss."), ("Coming from the winner's bracket, %(player)s started the match with a %(na)s-%(nb)s lead.", "Coming from the winner's bracket, %(player)s started the match with a %(na)s-%(nb)s lead."), ('%(player)s started the match with a %(na)s–%(nb)s lead from a previous match.', '%(player)s started the match with a %(na)s–%(nb)s lead from a previous match.'), ('%(player)s started the match with a %(na)s–%(nb)s lead.', '%(player)s started the match with a %(na)s–%(nb)s lead.'), ('%(player)s defeated %(opponent)s to qualify for %(event)s.', '%(player)s defeated %(opponent)s to qualify for %(event)s.'), ('%(player)s defeated %(opponents)s and %(opponent)s to qualify for %(event)s.', '%(player)s defeated %(opponents)s and %(opponent)s to qualify for %(event)s.'), ('%(player)s defeated %(opponent)s to qualify for %(event)s alongside %(otherplayer)s.', '%(player)s defeated %(opponent)s to qualify for %(event)s alongside %(otherplayer)s.'), ('%(player)s defeated %(opponents)s and %(opponent)s to qualify for %(event)s alongside %(otherplayer)s.', '%(player)s defeated %(opponents)s and %(opponent)s to qualify for %(event)s alongside %(otherplayer)s.'), ('%(player)s forfeited and was replaced by %(otherplayer)s who won a qualifier against %(opponent)s.', '%(player)s forfeited and was replaced by %(otherplayer)s who won a qualifier against %(opponent)s.'), ('Qualification match to replace %(player)s.', 'Qualification match to replace %(player)s.'), ('%(players)s and %(player)s played tiebreakers for the %(num)s spots.', '%(players)s and %(player)s played tiebreakers for the %(num)s spots.'), ('Game %(num)s lasted for %(h)s hours, %(m)s minutes and %(s)s seconds.', 'Game %(num)s lasted for %(h)s hours, %(m)s minutes and %(s)s seconds.'), ('%(player)s won %(num)s-X, assumed to be %(num)s-0.', '%(player)s won %(num)s-X, assumed to be %(num)s-0.'), ('Tiebreaker game.', 'Tiebreaker game.'), ('%(player)s was seeded.', '%(player)s was seededs.'), ('%(players)s and %(player)s were seeded.', '%(players)s and %(player)s were seeded.'), ('Game %(num)s was a draw and had to be replayed.', 'Game %(num)s was a draw and had to be replayed.')], verbose_name='Message', max_length=1000)),
                ('params', models.CharField(default='', verbose_name='Parameters', max_length=1000)),
                ('event', models.ForeignKey(to='ratings.Event', null=True)),
                ('group', models.ForeignKey(to='ratings.Group', null=True)),
                ('match', models.ForeignKey(to='ratings.Match', null=True)),
            ],
            options={
                'db_table': 'message',
            },
        ),
        migrations.CreateModel(
            name='Period',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('start', models.DateField(db_index=True, verbose_name='Start date', help_text='Start date')),
                ('end', models.DateField(db_index=True, verbose_name='End date', help_text='End date')),
                ('computed', models.BooleanField(default=False, db_index=True, verbose_name='Computed')),
                ('needs_recompute', models.BooleanField(default=False, db_index=True, verbose_name='Requires recomputation', help_text='True if this period needs to be recomputed')),
                ('num_retplayers', models.IntegerField(default=0, verbose_name='# returning players', help_text='Number of returning players')),
                ('num_newplayers', models.IntegerField(default=0, verbose_name='# new players', help_text='Number of new players')),
                ('num_games', models.IntegerField(default=0, verbose_name='# games', help_text='Number of games played')),
                ('dom_p', models.FloatField(null=True, verbose_name='Protoss OP value', help_text='Protoss OP value')),
                ('dom_t', models.FloatField(null=True, verbose_name='Terran OP value', help_text='Terran OP value')),
                ('dom_z', models.FloatField(null=True, verbose_name='Zerg OP value', help_text='Zerg OP value')),
            ],
            options={
                'db_table': 'period',
            },
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('tag', models.CharField(db_index=True, max_length=30, verbose_name='In-game name', help_text='Player tag')),
                ('name', models.CharField(null=True, max_length=100, blank=True, verbose_name='Full name', help_text='Full name')),
                ('romanized_name', models.CharField(null=True, max_length=100, blank=True, verbose_name='Romanized name', help_text='Full romanized version of name')),
                ('birthday', models.DateField(null=True, blank=True, verbose_name='Birthday', help_text='Birthday')),
                ('mcnum', models.IntegerField(default=None, null=True, blank=True, verbose_name='MC number', help_text='MC number')),
                ('tlpd_id', models.IntegerField(null=True, blank=True, verbose_name='TLPD ID', help_text='TLPD id')),
                ('tlpd_db', models.IntegerField(null=True, blank=True, verbose_name='TLPD Databases', help_text='TLPD databases (bit-flag value, 1=WoL KR, 2=WoL intl, 4=HotS, 8=HotS beta, 16=WoL beta)')),
                ('lp_name', models.CharField(null=True, max_length=200, blank=True, verbose_name='Liquipedia title', help_text='Liquipedia title')),
                ('sc2e_id', models.IntegerField(null=True, blank=True, verbose_name='SC2Earnings.com ID', help_text='SC2Earnings.com ID')),
                ('country', models.CharField(db_index=True, blank=True, max_length=2, choices=[('AF', 'Afghanistan'), ('AL', 'Albania'), ('DZ', 'Algeria'), ('AS', 'American Samoa'), ('AD', 'Andorra'), ('AO', 'Angola'), ('AI', 'Anguilla'), ('AQ', 'Antarctica'), ('AG', 'Antigua and Barbuda'), ('AR', 'Argentina'), ('AM', 'Armenia'), ('AW', 'Aruba'), ('AU', 'Australia'), ('AT', 'Austria'), ('AZ', 'Azerbaijan'), ('BS', 'Bahamas'), ('BH', 'Bahrain'), ('BD', 'Bangladesh'), ('BB', 'Barbados'), ('BY', 'Belarus'), ('BE', 'Belgium'), ('BZ', 'Belize'), ('BJ', 'Benin'), ('BM', 'Bermuda'), ('BT', 'Bhutan'), ('BO', 'Bolivia'), ('BA', 'Bosnia and Herzegovina'), ('BW', 'Botswana'), ('BV', 'Bouvet Island'), ('BR', 'Brazil'), ('IO', 'British Indian Ocean Territory'), ('VG', 'British Virgin Islands'), ('BN', 'Brunei'), ('BG', 'Bulgaria'), ('BF', 'Burkina Faso'), ('BI', 'Burundi'), ('KH', 'Cambodia'), ('CM', 'Cameroon'), ('CA', 'Canada'), ('CV', 'Cape Verde'), ('KY', 'Cayman Islands'), ('CF', 'Central African Republic'), ('TD', 'Chad'), ('CL', 'Chile'), ('CN', 'China'), ('CX', 'Christmas Island'), ('CC', 'Cocos (Keeling) Islands'), ('CO', 'Colombia'), ('KM', 'Comoros'), ('CD', 'Congo'), ('CG', 'Congo'), ('CK', 'Cook Islands'), ('CR', 'Costa Rica'), ('CI', "Cote d'Ivoire"), ('HR', 'Croatia'), ('CU', 'Cuba'), ('CY', 'Cyprus'), ('CZ', 'Czech Republic'), ('DK', 'Denmark'), ('DJ', 'Djibouti'), ('DM', 'Dominica'), ('DO', 'Dominican Republic'), ('EC', 'Ecuador'), ('EG', 'Egypt'), ('SV', 'El Salvador'), ('GQ', 'Equatorial Guinea'), ('ER', 'Eritrea'), ('EE', 'Estonia'), ('ET', 'Ethiopia'), ('FK', 'Falkland Islands (Malvinas)'), ('FO', 'Faroe Islands'), ('FJ', 'Fiji'), ('FI', 'Finland'), ('FR', 'France'), ('GF', 'French Guiana'), ('PF', 'French Polynesia'), ('TF', 'French Southern Territories'), ('GA', 'Gabon'), ('GM', 'Gambia'), ('GE', 'Georgia'), ('DE', 'Germany'), ('GH', 'Ghana'), ('GI', 'Gibraltar'), ('GR', 'Greece'), ('GL', 'Greenland'), ('GD', 'Grenada'), ('GP', 'Guadeloupe'), ('GU', 'Guam'), ('GT', 'Guatemala'), ('GG', 'Guernsey'), ('GN', 'Guinea'), ('GW', 'Guinea-Bissau'), ('GY', 'Guyana'), ('HT', 'Haiti'), ('HM', 'Heard Island and McDonald Islands'), ('HN', 'Honduras'), ('HK', 'Hong Kong'), ('HU', 'Hungary'), ('IS', 'Iceland'), ('IN', 'India'), ('ID', 'Indonesia'), ('IR', 'Iran'), ('IQ', 'Iraq'), ('IE', 'Ireland'), ('IM', 'Isle of Man'), ('IL', 'Israel'), ('IT', 'Italy'), ('JM', 'Jamaica'), ('JP', 'Japan'), ('JE', 'Jersey'), ('JO', 'Jordan'), ('KZ', 'Kazakhstan'), ('KE', 'Kenya'), ('KI', 'Kiribati'), ('KW', 'Kuwait'), ('KG', 'Kyrgyzstan'), ('LA', 'Laos'), ('LV', 'Latvia'), ('LB', 'Lebanon'), ('LS', 'Lesotho'), ('LR', 'Liberia'), ('LY', 'Libya'), ('LI', 'Liechtenstein'), ('LT', 'Lithuania'), ('LU', 'Luxembourg'), ('MO', 'Macao'), ('MK', 'Macedonia'), ('MG', 'Madagascar'), ('MW', 'Malawi'), ('MY', 'Malaysia'), ('MV', 'Maldives'), ('ML', 'Mali'), ('MT', 'Malta'), ('MH', 'Marshall Islands'), ('MQ', 'Martinique'), ('MR', 'Mauritania'), ('MU', 'Mauritius'), ('YT', 'Mayotte'), ('MX', 'Mexico'), ('FM', 'Micronesia'), ('MD', 'Moldova'), ('MN', 'Mongolia'), ('ME', 'Montenegro'), ('MS', 'Montserrat'), ('MA', 'Morocco'), ('MZ', 'Mozambique'), ('MM', 'Myanmar'), ('NA', 'Namibia'), ('NR', 'Nauru'), ('NP', 'Nepal'), ('NL', 'Netherlands'), ('AN', 'Netherlands Antilles'), ('NC', 'New Caledonia'), ('NZ', 'New Zealand'), ('NI', 'Nicaragua'), ('NE', 'Niger'), ('NG', 'Nigeria'), ('NU', 'Niue'), ('NF', 'Norfolk Island'), ('KP', 'North Korea'), ('MP', 'Northern Mariana Islands'), ('NO', 'Norway'), ('OM', 'Oman'), ('PK', 'Pakistan'), ('PW', 'Palau'), ('PS', 'Palestinian Territory'), ('PA', 'Panama'), ('PG', 'Papua New Guinea'), ('PY', 'Paraguay'), ('PE', 'Peru'), ('PH', 'Philippines'), ('PN', 'Pitcairn Islands'), ('PL', 'Poland'), ('PT', 'Portugal'), ('PR', 'Puerto Rico'), ('QA', 'Qatar'), ('RE', 'Reunion'), ('RO', 'Romania'), ('RU', 'Russia'), ('RW', 'Rwanda'), ('BL', 'Saint Barthelemy'), ('SH', 'Saint Helena'), ('KN', 'Saint Kitts and Nevis'), ('LC', 'Saint Lucia'), ('MF', 'Saint Martin'), ('PM', 'Saint Pierre and Miquelon'), ('VC', 'Saint Vincent and the Grenadines'), ('WS', 'Samoa'), ('SM', 'San Marino'), ('ST', 'Sao Tome and Principe'), ('SA', 'Saudi Arabia'), ('SN', 'Senegal'), ('RS', 'Serbia'), ('SL', 'Sierra Leone'), ('SG', 'Singapore'), ('SK', 'Slovakia'), ('SI', 'Slovenia'), ('SB', 'Solomon Islands'), ('SO', 'Somalia'), ('ZA', 'South Africa'), ('GS', 'South Georgia and the South Sandwich Islands'), ('KR', 'South Korea'), ('ES', 'Spain'), ('LK', 'Sri Lanka'), ('SD', 'Sudan'), ('SR', 'Suriname'), ('SJ', 'Svalbard & Jan Mayen Islands'), ('SZ', 'Swaziland'), ('SE', 'Sweden'), ('CH', 'Switzerland'), ('SY', 'Syria'), ('TW', 'Taiwan'), ('TZ', 'Tanzania'), ('TH', 'Thailand'), ('TL', 'Timor-Leste'), ('TG', 'Togo'), ('TK', 'Tokelau'), ('TO', 'Tonga'), ('TT', 'Trinidad and Tobago'), ('TN', 'Tunisia'), ('TR', 'Turkey'), ('TM', 'Turkmenistan'), ('TC', 'Turks and Caicos Islands'), ('TV', 'Tuvalu'), ('UG', 'Uganda'), ('UA', 'Ukraine'), ('AE', 'United Arab Emirates'), ('UK', 'United Kingdom'), ('UM', 'United States Minor Outlying Islands'), ('VI', 'United States Virgin Islands'), ('US', 'United States of America'), ('UY', 'Uruguay'), ('UZ', 'Uzbekistan'), ('VU', 'Vanuatu'), ('VA', 'Vatican City'), ('VE', 'Venezuela'), ('VN', 'Vietnam'), ('WF', 'Wallis and Futuna'), ('EH', 'Western Sahara'), ('YE', 'Yemen'), ('ZM', 'Zambia'), ('ZW', 'Zimbabwe'), ('AX', 'Åland Islands')], help_text='Country (ISO 3166-1 alpha-2)', verbose_name='Country', null=True)),
                ('race', models.CharField(db_index=True, max_length=1, choices=[('P', 'Protoss'), ('T', 'Terran'), ('Z', 'Zerg'), ('R', 'Random'), ('S', 'Switcher')], verbose_name='Race', help_text='Race (P, T, Z, R or S)')),
                ('dom_val', models.FloatField(null=True, blank=True, verbose_name='Domination', help_text='Domination score (PP)')),
            ],
            options={
                'ordering': ['tag'],
                'db_table': 'player',
            },
        ),
        migrations.CreateModel(
            name='PreMatch',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('pla_string', models.CharField(default='', null=True, blank=True, verbose_name='Player A (str)', max_length=200)),
                ('plb_string', models.CharField(default='', null=True, blank=True, verbose_name='Player A (str)', max_length=200)),
                ('sca', models.SmallIntegerField(verbose_name='Score for player A')),
                ('scb', models.SmallIntegerField(verbose_name='Score for player B')),
                ('date', models.DateField(verbose_name='Date')),
                ('rca', models.CharField(choices=[('P', 'Protoss'), ('T', 'Terran'), ('Z', 'Zerg'), ('R', 'Random')], null=True, verbose_name='Race A', max_length=1)),
                ('rcb', models.CharField(choices=[('P', 'Protoss'), ('T', 'Terran'), ('Z', 'Zerg'), ('R', 'Random')], null=True, verbose_name='Race B', max_length=1)),
            ],
            options={
                'verbose_name_plural': 'prematches',
                'db_table': 'prematch',
            },
        ),
        migrations.CreateModel(
            name='PreMatchGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('date', models.DateField(verbose_name='Date')),
                ('event', models.CharField(default='', blank=True, verbose_name='Event', max_length=200)),
                ('source', models.CharField(default='', null=True, blank=True, verbose_name='Source', max_length=500)),
                ('contact', models.CharField(default='', null=True, blank=True, verbose_name='Contact', max_length=200)),
                ('notes', models.TextField(default='', blank=True, verbose_name='Notes', null=True)),
                ('game', models.CharField(default='wol', choices=[('WoL', 'Wings of Liberty'), ('HotS', 'Heart of the Swarm'), ('LotV', 'Legacy of the Void')], verbose_name='Game', max_length=10)),
                ('offline', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name_plural': 'Prematch Groups',
                'verbose_name': 'Prematch Group',
                'db_table': 'prematchgroup',
            },
        ),
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('rating', models.FloatField(verbose_name='Rating', help_text='Mean rating')),
                ('rating_vp', models.FloatField(verbose_name='R-del vP', help_text='Adjustment vP')),
                ('rating_vt', models.FloatField(verbose_name='R-del vT', help_text='Adjustment vT')),
                ('rating_vz', models.FloatField(verbose_name='R-del vZ', help_text='Adjustment vZ')),
                ('dev', models.FloatField(verbose_name='RD', help_text='Mean rating deviation')),
                ('dev_vp', models.FloatField(verbose_name='RD vP', help_text='Extra rating deviation vP')),
                ('dev_vt', models.FloatField(verbose_name='RD vT', help_text='Extra rating deviation vT')),
                ('dev_vz', models.FloatField(verbose_name='RD vZ', help_text='Extra rating deviation vZ')),
                ('comp_rat', models.FloatField(null=True, blank=True, verbose_name='Perf', help_text='Mean performance rating (-1000: N/A, -2000: +INF, -3000: -INF)')),
                ('comp_rat_vp', models.FloatField(null=True, blank=True, verbose_name='P-del vP', help_text='Mean performance rating (-1000: N/A, -2000: +INF, -3000: -INF)')),
                ('comp_rat_vt', models.FloatField(null=True, blank=True, verbose_name='P-del vT', help_text='Mean performance rating (-1000: N/A, -2000: +INF, -3000: -INF)')),
                ('comp_rat_vz', models.FloatField(null=True, blank=True, verbose_name='P-del vZ', help_text='Mean performance rating (-1000: N/A, -2000: +INF, -3000: -INF)')),
                ('bf_rating', models.FloatField(default=0, verbose_name='BF', help_text='Mean backwards filtered rating')),
                ('bf_rating_vp', models.FloatField(default=0, verbose_name='BF-del vP', help_text='Backwards filtered adjustment vP')),
                ('bf_rating_vt', models.FloatField(default=0, verbose_name='BF-del vT', help_text='Backwards filtered adjustment vT')),
                ('bf_rating_vz', models.FloatField(default=0, verbose_name='BF-del vZ', help_text='Backwards filtered adjustment vZ')),
                ('bf_dev', models.FloatField(default=1, null=True, blank=True, verbose_name='BFD', help_text='Mean backwards filtered rating deviation')),
                ('bf_dev_vp', models.FloatField(default=1, null=True, blank=True, verbose_name='BFD vP', help_text='Extra backwards filtered rating deviation vP')),
                ('bf_dev_vt', models.FloatField(default=1, null=True, blank=True, verbose_name='BFD vT', help_text='Extra backwards filtered rating deviation vT')),
                ('bf_dev_vz', models.FloatField(default=1, null=True, blank=True, verbose_name='BFD vZ', help_text='Extra backwards filtered rating deviation vZ')),
                ('position', models.IntegerField(null=True, verbose_name='Rank', help_text='Mean rating rank (if active)')),
                ('position_vp', models.IntegerField(null=True, verbose_name='Rank vP', help_text='vP rating rank (if active)')),
                ('position_vt', models.IntegerField(null=True, verbose_name='Rank vT', help_text='vT rating rank (if active)')),
                ('position_vz', models.IntegerField(null=True, verbose_name='Rank vZ', help_text='vZ rating rank (if active)')),
                ('decay', models.IntegerField(default=0, verbose_name='Decay', help_text='Number of periods since last game')),
                ('domination', models.FloatField(null=True, blank=True, help_text='Difference from number 7 on rating list')),
                ('period', models.ForeignKey(to='ratings.Period', verbose_name='Period', help_text='This rating applies to the given period')),
                ('player', models.ForeignKey(to='ratings.Player', verbose_name='Player', help_text='This rating applies to the given player')),
                ('prev', models.ForeignKey(to='ratings.Rating', verbose_name='Previous rating', help_text='Previous rating for the same player', related_name='prevrating', null=True)),
            ],
            options={
                'ordering': ['period'],
                'db_table': 'rating',
            },
        ),
        migrations.CreateModel(
            name='Story',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('date', models.DateField(verbose_name='Date')),
                ('message', models.CharField(default='', choices=[('%(player)s wins %(event)s', '%(player)s wins %(event)s'), ('%(player)s defeats %(opponent)s and wins %(event)s', '%(player)s defeats %(opponent)s and wins %(event)s'), ('%(player)s wins %(event)s as a royal roader', '%(player)s wins %(event)s as a royal roader'), ('%(player)s defeats %(opponent)s and wins %(event)s as a royal roader', '%(player)s defeats %(opponent)s and wins %(event)s as a royal roader'), ('%(player)s all-kills %(team)s', '%(player)s all-kills %(team)s'), ('%(player)s all-kills %(team)s and wins %(event)s', '%(player)s all-kills %(team)s and wins %(event)s'), ('%(player)s finishes second in %(event)s', '%(player)s finishes second in %(event)s'), ('%(player)s finishes third in %(event)s', '%(player)s finishes third in %(event)s'), ('%(player)s finishes fourth in %(event)s', '%(player)s finishes fourth in %(event)s'), ('%(player)s finishes top 4 in %(event)s', '%(player)s finishes top 4 in %(event)s'), ('%(player)s finishes top 8 in %(event)s', '%(player)s finishes top 8 in %(event)s'), ('%(player)s switches to %(race)s', '%(player)s switches to %(race)s'), ('%(player)s switches back to %(race)s', '%(player)s switches back to %(race)s'), ('%(player)s switches from %(racea)s to %(raceb)s', '%(player)s switches from %(racea)s to %(raceb)s'), ('%(player)s switches from %(racea)s back to %(raceb)s', '%(player)s switches from %(racea)s back to %(raceb)s'), ('%(player)s defeats %(opponent)s and starts a %(num)s-kill spree in %(event)s', '%(player)s defeats %(opponent)s and starts a %(num)s-kill spree in %(event)s'), ('%(player)s loses to %(opponent)s, ending a %(num)s-kill spree in %(event)s', '%(player)s loses to %(opponent)s, ending a %(num)s-kill spree in %(event)s'), ('%(player)s fails to qualify for %(event)s', '%(player)s fails to qualify for %(event)s'), ('%(player)s fails to qualify for %(event)s after %(num)s appearances', '%(player)s fails to qualify for %(event)s after %(num)s appearances'), ('%(player)s attends their first event as a caster', '%(player)s attends their first event as a caster')], verbose_name='Message', max_length=1000)),
                ('params', models.CharField(default='', verbose_name='Parameters', max_length=1000)),
                ('event', models.ForeignKey(blank=True, to='ratings.Event', null=True)),
                ('player', models.ForeignKey(to='ratings.Player')),
            ],
            options={
                'verbose_name_plural': 'stories',
                'db_table': 'story',
                'ordering': ['date'],
            },
        ),
        migrations.CreateModel(
            name='WCSPoints',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('points', models.IntegerField(verbose_name='Points', help_text='Number of points awarded')),
                ('placement', models.IntegerField(verbose_name='Place', help_text='Placement')),
                ('event', models.ForeignKey(to='ratings.Event', verbose_name='Event', help_text='Event in which these WCS points was awarded')),
                ('player', models.ForeignKey(to='ratings.Player', verbose_name='Player', help_text='Player to which these WCS points was awarded')),
            ],
            options={
                'ordering': ['-points'],
                'db_table': 'wcspoints',
            },
        ),
        migrations.AddField(
            model_name='prematch',
            name='group',
            field=models.ForeignKey(verbose_name='Group', to='ratings.PreMatchGroup'),
        ),
        migrations.AddField(
            model_name='prematch',
            name='pla',
            field=models.ForeignKey(blank=True, verbose_name='Player A', to='ratings.Player', related_name='prematch_pla', null=True),
        ),
        migrations.AddField(
            model_name='prematch',
            name='plb',
            field=models.ForeignKey(blank=True, verbose_name='Player B', to='ratings.Player', related_name='prematch_plb', null=True),
        ),
        migrations.AddField(
            model_name='player',
            name='current_rating',
            field=models.ForeignKey(to='ratings.Rating', blank=True, help_text='Current rating', related_name='current', null=True),
        ),
        migrations.AddField(
            model_name='player',
            name='dom_end',
            field=models.ForeignKey(to='ratings.Period', blank=True, help_text='End of domination period', related_name='player_dom_end', null=True),
        ),
        migrations.AddField(
            model_name='player',
            name='dom_start',
            field=models.ForeignKey(to='ratings.Period', blank=True, help_text='Start of domination period', related_name='player_dom_start', null=True),
        ),
        migrations.AddField(
            model_name='message',
            name='player',
            field=models.ForeignKey(to='ratings.Player', null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='period',
            field=models.ForeignKey(to='ratings.Period', help_text='Period in which the match was played'),
        ),
        migrations.AddField(
            model_name='match',
            name='pla',
            field=models.ForeignKey(to='ratings.Player', verbose_name='Player A', help_text='Player A', related_name='match_pla'),
        ),
        migrations.AddField(
            model_name='match',
            name='plb',
            field=models.ForeignKey(to='ratings.Player', verbose_name='Player B', help_text='Player B', related_name='match_plb'),
        ),
        migrations.AddField(
            model_name='match',
            name='rta',
            field=models.ForeignKey(to='ratings.Rating', verbose_name='Rating A', help_text='Rating for player A at the time the match was played', related_name='rta', null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='rtb',
            field=models.ForeignKey(to='ratings.Rating', verbose_name='Rating B', help_text='Rating for player B at the time the match was played', related_name='rtb', null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='submitter',
            field=models.ForeignKey(blank=True, verbose_name='Submitter', to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='groupmembership',
            name='player',
            field=models.ForeignKey(to='ratings.Player'),
        ),
        migrations.AddField(
            model_name='group',
            name='members',
            field=models.ManyToManyField(to='ratings.Player', through='ratings.GroupMembership'),
        ),
        migrations.AddField(
            model_name='event',
            name='family',
            field=models.ManyToManyField(to='ratings.Event', through='ratings.EventAdjacency'),
        ),
        migrations.AddField(
            model_name='event',
            name='parent',
            field=models.ForeignKey(to='ratings.Event', blank=True, help_text='Parent event', related_name='parent_event', null=True),
        ),
        migrations.AddField(
            model_name='earnings',
            name='event',
            field=models.ForeignKey(to='ratings.Event', verbose_name='Event', help_text='Event in which this prize was awarded'),
        ),
        migrations.AddField(
            model_name='earnings',
            name='player',
            field=models.ForeignKey(to='ratings.Player', verbose_name='Player', help_text='Player to which this prize was awarded'),
        ),
        migrations.AddField(
            model_name='alias',
            name='group',
            field=models.ForeignKey(to='ratings.Group', null=True),
        ),
        migrations.AddField(
            model_name='alias',
            name='player',
            field=models.ForeignKey(to='ratings.Player', null=True),
        ),
    ]
