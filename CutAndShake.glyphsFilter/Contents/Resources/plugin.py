# encoding: utf-8

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
from random import random, randint
from GlyphsApp import *
from GlyphsApp.plugins import *

class CutAndShake(FilterWithDialog):
	goodMeasure = 5.0
	
	# Definitions of IBOutlets
	dialog = objc.IBOutlet()
	numberOfCutsField = objc.IBOutlet()
	maxMoveField = objc.IBOutlet()
	maxRotateField = objc.IBOutlet()
	
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': u'Cut and Shake',
			'de': u'Schneiden und schütteln',
			'fr': u'Couper et secouer',
			'es': u'Cortar y agitar',
		})

		self.actionButtonLabel = Glyphs.localize({
			'en': u'Apply',
			'de': u'Anwenden',
			'fr': u'Appliquer',
			'es': u'Aplicar',
		})
		
		# Load dialog from .nib (without .extension)
		self.loadNib('IBdialog', __file__)
	
	# On dialog show
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
	def filter(self, layer, inEditView, customParameters):
		# Called through UI, use stored value
		numberOfCuts = int(Glyphs.defaults['com.mekkablue.CutAndShake.numberOfCuts'])
		maxMove = float(Glyphs.defaults['com.mekkablue.CutAndShake.maxMove'])
		maxRotate = float(Glyphs.defaults['com.mekkablue.CutAndShake.maxRotate'])
		
		# Called on font export, overwrite with values from customParameters:
		if customParameters.has_key('cuts'):
			numberOfCuts = int(customParameters['cuts'])
		if customParameters.has_key('move'):
			maxMove = abs(customParameters['move'])
		if customParameters.has_key('rotate'):
			maxRotate = abs(customParameters['rotate'])
		
		# process the layer:
		self.randomCutLayer( layer, numberOfCuts )
		self.randomMovePaths( layer, maxMove )
		self.randomRotatePaths( layer, maxRotate )
	
	def generateCustomParameter( self ):
		return "%s; cuts:%s; move:%s; rotate:%s" % (
			self.__class__.__name__,
			Glyphs.defaults['com.mekkablue.CutAndShake.numberOfCuts'],
			Glyphs.defaults['com.mekkablue.CutAndShake.maxMove'],
			Glyphs.defaults['com.mekkablue.CutAndShake.maxRotate'],
		)
	
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__

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

	def randomMovePaths( self, thisLayer, maximumMove ):
		for thisPath in thisLayer.paths:
			xMove = self.somewhereBetween( -maximumMove/(2**0.5), maximumMove/(2**0.5) )
			yMove = self.somewhereBetween( -maximumMove/(2**0.5), maximumMove/(2**0.5) )
			shift = NSAffineTransform.transform()
			shift.translateXBy_yBy_( xMove, yMove )
			thisPath.applyTransform( shift.transformStruct() )
		
	def somewhereBetween( self, minimum, maximum ):
		minMaxRange = maximum - minimum
		randomFloat = minimum + random() * minMaxRange
		return randomFloat

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
			