# encoding: utf-8
from __future__ import division, print_function, unicode_literals

###########################################################################################################
#
#
#	Filter with dialog Plugin
#
#	Read the docs:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates/Filter%20with%20Dialog
#
#	For help on the use of Interface Builder:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates
#
#
###########################################################################################################

import objc
from GlyphsApp import *
from GlyphsApp.plugins import *
from random import random, randint

class CutAndShake(FilterWithDialog):
	goodMeasure = 5.0
	
	# Definitions of IBOutlets
	dialog = objc.IBOutlet()
	numberOfCutsField = objc.IBOutlet()
	maxMoveField = objc.IBOutlet()
	maxRotateField = objc.IBOutlet()
	
	@objc.python_method
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': u'Cut and Shake',
			'de': u'Schneiden und schütteln',
			'fr': u'Couper et secouer',
			'es': u'Cortar y agitar',
			'zh': u'🤺碎片化',
		})

		self.actionButtonLabel = Glyphs.localize({
			'en': u'Apply',
			'de': u'Anwenden',
			'fr': u'Appliquer',
			'es': u'Aplicar',
			'zh': u'应用',
		})
		
		# Load dialog from .nib (without .extension)
		self.loadNib('IBdialog', __file__)
	
	# On dialog show
	@objc.python_method
	def start(self):
		
		# Default settings
		NSUserDefaults.standardUserDefaults().registerDefaults_({
				"com.mekkablue.CutAndShake.numberOfCuts": 5,
				"com.mekkablue.CutAndShake.maxMove": 50,
				"com.mekkablue.CutAndShake.maxRotate": 20,
			})
		
		# Set value of text field
		self.numberOfCutsField.setStringValue_(Glyphs.defaults['com.mekkablue.CutAndShake.numberOfCuts'])
		self.maxMoveField.setStringValue_(Glyphs.defaults['com.mekkablue.CutAndShake.maxMove'])
		self.maxRotateField.setStringValue_(Glyphs.defaults['com.mekkablue.CutAndShake.maxRotate'])
		
		# Set focus to text field
		self.numberOfCutsField.becomeFirstResponder()
		
	# Action triggered by UI
	@objc.IBAction
	def setNumberOfCuts_( self, sender ):
		Glyphs.defaults['com.mekkablue.CutAndShake.numberOfCuts'] = sender.intValue()
		self.update()
	
	@objc.IBAction
	def setMaxMove_( self, sender ):
		Glyphs.defaults['com.mekkablue.CutAndShake.maxMove'] = sender.floatValue()
		self.update()
	
	@objc.IBAction
	def setMaxRotate_( self, sender ):
		Glyphs.defaults['com.mekkablue.CutAndShake.maxRotate'] = sender.floatValue()
		self.update()
	
	# Actual filter
	@objc.python_method
	def filter(self, layer, inEditView, customParameters):
		# Called through UI, use stored value
		numberOfCuts = int(Glyphs.defaults['com.mekkablue.CutAndShake.numberOfCuts'])
		maxMove = float(Glyphs.defaults['com.mekkablue.CutAndShake.maxMove'])
		maxRotate = float(Glyphs.defaults['com.mekkablue.CutAndShake.maxRotate'])
		
		# Called on font export, overwrite with values from customParameters:
		if 'cuts' in customParameters:
			numberOfCuts = int(customParameters['cuts'])
		if 'move' in customParameters:
			maxMove = abs(customParameters['move'])
		if 'rotate' in customParameters:
			maxRotate = abs(customParameters['rotate'])
		
		# process the layer:
		self.randomCutLayer( layer, numberOfCuts )
		self.randomMovePaths( layer, maxMove )
		self.randomRotatePaths( layer, maxRotate )
	
	@objc.python_method
	def generateCustomParameter( self ):
		return "%s; cuts:%s; move:%s; rotate:%s" % (
			self.__class__.__name__,
			Glyphs.defaults['com.mekkablue.CutAndShake.numberOfCuts'],
			Glyphs.defaults['com.mekkablue.CutAndShake.maxMove'],
			Glyphs.defaults['com.mekkablue.CutAndShake.maxRotate'],
		)
	
	@objc.python_method
	def randomCutLayer( self, thisLayer, numberOfCuts ):
		lowestY = thisLayer.bounds.origin.y - self.goodMeasure
		highestY = thisLayer.bounds.origin.y + thisLayer.bounds.size.height + self.goodMeasure
		leftmostX = thisLayer.bounds.origin.x - self.goodMeasure
		rightmostX = thisLayer.bounds.origin.x + thisLayer.bounds.size.width + self.goodMeasure
		for i in range( numberOfCuts ):
			# make either horizontal or vertical cut:
			if randint( 0, 1 ) == 0:
				point1 = NSPoint( leftmostX,  self.somewhereBetween( lowestY, highestY ) )
				point2 = NSPoint( rightmostX, self.somewhereBetween( lowestY, highestY ) )
			else:
				point1 = NSPoint( self.somewhereBetween( leftmostX, rightmostX ), lowestY  )
				point2 = NSPoint( self.somewhereBetween( leftmostX, rightmostX ), highestY )
			thisLayer.cutBetweenPoints( point1, point2 )

	@objc.python_method
	def randomMovePaths( self, thisLayer, maximumMove ):
		for thisPath in thisLayer.paths:
			xMove = self.somewhereBetween( -maximumMove/(2**0.5), maximumMove/(2**0.5) )
			yMove = self.somewhereBetween( -maximumMove/(2**0.5), maximumMove/(2**0.5) )
			shift = NSAffineTransform.transform()
			shift.translateXBy_yBy_( xMove, yMove )
			thisPath.applyTransform( shift.transformStruct() )
	
	@objc.python_method
	def somewhereBetween( self, minimum, maximum ):
		minMaxRange = maximum - minimum
		randomFloat = minimum + random() * minMaxRange
		return randomFloat

	@objc.python_method
	def randomRotatePaths( self, thisLayer, maximumRotate ):
		for thisPath in thisLayer.paths:
			centerX = thisPath.bounds.origin.x + thisPath.bounds.size.width / 2.0
			centerY = thisPath.bounds.origin.y + thisPath.bounds.size.height / 2.0
			degrees = self.somewhereBetween( -maximumRotate, maximumRotate )
			rotation = NSAffineTransform.transform()
			rotation.translateXBy_yBy_( centerX, centerY )
			rotation.rotateByDegrees_( degrees )
			rotation.translateXBy_yBy_( -centerX, -centerY )
			thisPath.applyTransform( rotation.transformStruct() )

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__

