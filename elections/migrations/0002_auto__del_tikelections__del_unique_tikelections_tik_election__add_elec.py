# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'TikElections', fields ['tik', 'election']
        db.delete_unique('elections_tikelections', ['tik_id', 'election_id'])

        # Deleting model 'TikElections'
        db.delete_table('elections_tikelections')

        # Adding model 'ElectionTIKs'
        db.create_table('elections_electiontiks', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['elections.Election'])),
            ('tik', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.Location'])),
        ))
        db.send_create_signal('elections', ['ElectionTIKs'])

        # Adding unique constraint on 'ElectionTIKs', fields ['election', 'tik']
        db.create_unique('elections_electiontiks', ['election_id', 'tik_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'ElectionTIKs', fields ['election', 'tik']
        db.delete_unique('elections_electiontiks', ['election_id', 'tik_id'])

        # Adding model 'TikElections'
        db.create_table('elections_tikelections', (
            ('tik', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.Location'])),
            ('election', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['elections.Election'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('elections', ['TikElections'])

        # Adding unique constraint on 'TikElections', fields ['tik', 'election']
        db.create_unique('elections_tikelections', ['tik_id', 'election_id'])

        # Deleting model 'ElectionTIKs'
        db.delete_table('elections_electiontiks')


    models = {
        'elections.election': {
            'Meta': {'object_name': 'Election'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'vrn': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True'})
        },
        'elections.electiontiks': {
            'Meta': {'unique_together': "(('election', 'tik'),)", 'object_name': 'ElectionTIKs'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['elections.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'tik': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['locations.Location']"})
        },
        'elections.electionuiks': {
            'Meta': {'unique_together': "(('election', 'uik'),)", 'object_name': 'ElectionUIKs'},
            'election': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['elections.Election']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'uik': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['elections.UIK']"})
        },
        'elections.uik': {
            'Meta': {'unique_together': "(('tik', 'date', 'number'),)", 'object_name': 'UIK'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number': ('django.db.models.fields.IntegerField', [], {}),
            'tik': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['locations.Location']"}),
            'tvd': ('django.db.models.fields.BigIntegerField', [], {})
        },
        'locations.location': {
            'Meta': {'object_name': 'Location'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'country_related'", 'null': 'True', 'to': "orm['locations.Location']"}),
            'data': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150', 'db_index': 'True'}),
            'postcode': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'region': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'in_region'", 'null': 'True', 'to': "orm['locations.Location']"}),
            'region_code': ('django.db.models.fields.IntegerField', [], {}),
            'region_name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'root': ('django.db.models.fields.IntegerField', [], {}),
            'telephone': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'tvd': ('django.db.models.fields.BigIntegerField', [], {}),
            'vrnkomis': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'vrnorg': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'x_coord': ('django.db.models.fields.FloatField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'y_coord': ('django.db.models.fields.FloatField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['elections']