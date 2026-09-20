//
//  CutAndShake.m
//  CutAndShake
//
//  Rainer Erich Scheichelbauer | mekkablue
//  Native Cocoa/ObjC version of the CutAndShake Glyphs filter plugin.
//
//  Cuts glyphs with random angled lines, then randomly moves and rotates
//  the resulting path fragments.
//

#import "CutAndShake.h"
#import <GlyphsCore/GlyphsCore.h>
#import <GlyphsApp/GSCallbackHandler.h>

// +cutPathsInLayer:forPoint:endPoint: is what GSLayer.cutBetweenPoints() calls
// in the Python wrapper. The class holding it is looked up at runtime, so the
// selector is declared here to give the compiler a signature to work with.
@interface NSObject (GlyphsCutPathsInLayer)
+ (void)cutPathsInLayer:(GSLayer *)layer forPoint:(NSPoint)point endPoint:(NSPoint)endPoint;
@end

@interface CutAndShake ()
+ (void)registerUserDefaults;
- (void)applyFilterToLayer:(GSLayer *)layer
              numberOfCuts:(NSInteger)numberOfCuts
                   maxMove:(CGFloat)maxMove
                 maxRotate:(CGFloat)maxRotate;
@end

// NSUserDefaults keys
static NSString *const kNumberOfCuts = @"com.mekkablue.CutAndShake.numberOfCuts";
static NSString *const kMaxMove      = @"com.mekkablue.CutAndShake.maxMove";
static NSString *const kMaxRotate    = @"com.mekkablue.CutAndShake.maxRotate";

// Extra margin around the glyph bounds when generating cut lines
static const CGFloat kGoodMeasure = 5.0;

/**
 The tool class that performs the cutting.
 Glyphs 4 calls it GlyphsToolKnife, Glyphs 3 called it GlyphsToolOther.
 */
static Class CutPathsToolClass(void) {
	static Class toolClass = Nil;
	static dispatch_once_t onceToken;
	dispatch_once(&onceToken, ^{
		toolClass = NSClassFromString(@"GlyphsToolKnife");
		if (!toolClass) {
			toolClass = NSClassFromString(@"GlyphsToolOther");
		}
	});
	return toolClass;
}

@implementation CutAndShake {
	// Glyphs 4 no longer provides a _view ivar in GSFilterPlugin, so the
	// plugin brings its own. Without it the bundle fails to load in Glyphs 4
	// with a missing _OBJC_IVAR_$_GSFilterPlugin._view symbol.
	NSView *_view;
}

- (instancetype)init {
	self = [super init];
	if (self) {
		[[self class] registerUserDefaults];
	}
	return self;
}

+ (void)registerUserDefaults {
	[[NSUserDefaults standardUserDefaults] registerDefaults:@{
		kNumberOfCuts: @5,
		kMaxMove:      @50,
		kMaxRotate:    @20,
	}];
}

#pragma mark - GSFilterPlugin required methods

- (NSUInteger)interfaceVersion {
	// Distinguishes the API version the plugin was built for.
	return 1;
}

- (NSString *)title {
	// Return the localised menu name.
	// Glyphs picks the best match for the current UI language.
	NSDictionary *names = @{
		@"en": @"Cut and Shake",
		@"de": @"Schneiden und schütteln",
		@"fr": @"Couper et secouer",
		@"es": @"Cortar y agitar",
		@"zh": @"🤺碎片化",
	};
	NSString *lang = [[[NSBundle mainBundle] preferredLocalizations] firstObject] ?: @"en";
	return names[lang] ?: names[@"en"];
}

- (NSString *)actionName {
	// The label of the Apply button in the filter dialog.
	NSDictionary *labels = @{
		@"en": @"Apply",
		@"de": @"Anwenden",
		@"fr": @"Appliquer",
		@"es": @"Aplicar",
		@"zh": @"应用",
	};
	NSString *lang = [[[NSBundle mainBundle] preferredLocalizations] firstObject] ?: @"en";
	return labels[lang] ?: labels[@"en"];
}

- (NSString *)keyEquivalent {
	// Return nil — no fixed keyboard shortcut (users set their own in System Settings).
	return nil;
}

#pragma mark - Dialog / View

- (NSView *)view {
	if (!_view) {
		[[NSBundle bundleForClass:[self class]]
			loadNibNamed:@"IBdialog"
			owner:self
			topLevelObjects:nil];
	}
	return _view;
}

- (NSError *)setup {
	// Called just before the dialog is shown.  Restore saved values and
	// push them into the text fields.
	[super setup];
	[[self class] registerUserDefaults];

	NSUserDefaults *ud = [NSUserDefaults standardUserDefaults];
	_numberOfCutsField.integerValue = [ud integerForKey:kNumberOfCuts];
	_maxMoveField.doubleValue       = [ud doubleForKey:kMaxMove];
	_maxRotateField.doubleValue     = [ud doubleForKey:kMaxRotate];

	// Show an initial preview right away.
	[self process:nil];
	return nil;
}

#pragma mark - IBActions

- (IBAction)setNumberOfCuts:(id)sender {
	[[NSUserDefaults standardUserDefaults]
		setInteger:[(NSTextField *)sender integerValue]
		forKey:kNumberOfCuts];
	[self process:nil];
}

- (IBAction)setMaxMove:(id)sender {
	[[NSUserDefaults standardUserDefaults]
		setDouble:[(NSTextField *)sender doubleValue]
		forKey:kMaxMove];
	[self process:nil];
}

- (IBAction)setMaxRotate:(id)sender {
	[[NSUserDefaults standardUserDefaults]
		setDouble:[(NSTextField *)sender doubleValue]
		forKey:kMaxRotate];
	[self process:nil];
}

#pragma mark - process: (interactive / live preview)

/**
 Called each time the user changes a parameter in the dialog.
 Restores each working layer from the corresponding shadow layer
 (the frozen copy Glyphs made before the filter was first applied),
 then runs the filter, then hands control back to Glyphs via
 [super process:nil].
 */
- (void)process:(id)sender {
	NSUserDefaults *ud = [NSUserDefaults standardUserDefaults];
	NSInteger numberOfCuts = [ud integerForKey:kNumberOfCuts];
	CGFloat   maxMove      = [ud doubleForKey:kMaxMove];
	CGFloat   maxRotate    = [ud doubleForKey:kMaxRotate];

	for (NSUInteger k = 0; k < _shadowLayers.count; k++) {
		GSLayer *shadowLayer = _shadowLayers[k];
		GSLayer *layer       = _layers[k];

		// Restore to the pre-filter state from the shadow copy.
		layer.shapes    = [[NSMutableArray alloc] initWithArray:shadowLayer.shapes copyItems:YES];
		layer.selection = [NSMutableOrderedSet new];

		// Restore selection on individual nodes when the user works
		// in the Edit view with a sub-selection.
		if (shadowLayer.selection.count > 0 && _checkSelection) {
			for (NSUInteger i = 0; i < shadowLayer.shapes.count; i++) {
				GSPath *shadowPath = (GSPath *)[shadowLayer objectInShapesAtIndex:i];
				if (![shadowPath isKindOfClass:[GSPath class]]) continue;
				GSPath *layerPath = (GSPath *)[layer objectInShapesAtIndex:i];
				for (NSUInteger j = 0; j < shadowPath.nodes.count; j++) {
					GSNode *shadowNode = [shadowPath nodeAtIndex:j];
					if ([shadowLayer.selection containsObject:shadowNode]) {
						[layer addSelection:[layerPath nodeAtIndex:j]];
					}
				}
			}
		}

		[self applyFilterToLayer:layer
		            numberOfCuts:numberOfCuts
		                 maxMove:maxMove
		               maxRotate:maxRotate];
		[layer clearSelection];
	}
	[super process:nil];
}

#pragma mark - Custom parameter string

- (NSString *)customParameterString {
	NSUserDefaults *ud = [NSUserDefaults standardUserDefaults];
	return [NSString stringWithFormat:@"%@; cuts:%ld; move:%.1f; rotate:%.1f",
		NSStringFromClass([self class]),
		(long)[ud integerForKey:kNumberOfCuts],
		[ud doubleForKey:kMaxMove],
		[ud doubleForKey:kMaxRotate]];
}

#pragma mark - Export / batch processing

- (void)processFont:(GSFont *)font withArguments:(NSArray *)arguments {
	// Called when the filter is invoked as a Custom Parameter at export.
	// arguments[0] is the class name; the remaining items are key:value pairs.
	[[self class] registerUserDefaults];

	NSUserDefaults *ud = [NSUserDefaults standardUserDefaults];
	NSInteger numberOfCuts = [ud integerForKey:kNumberOfCuts];
	CGFloat   maxMove      = [ud doubleForKey:kMaxMove];
	CGFloat   maxRotate    = [ud doubleForKey:kMaxRotate];

	// Parse key:value arguments supplied via the custom parameter.
	NSCharacterSet *whitespace = [NSCharacterSet whitespaceCharacterSet];
	for (NSUInteger i = 1; i < arguments.count; i++) {
		NSString *arg = [arguments[i] stringByTrimmingCharactersInSet:whitespace];
		if ([arg hasPrefix:@"include:"] || [arg hasPrefix:@"exclude:"]) continue;
		NSArray  *kv  = [arg componentsSeparatedByString:@":"];
		if (kv.count != 2) continue;
		NSString *key   = [kv[0] stringByTrimmingCharactersInSet:whitespace];
		NSString *value = [kv[1] stringByTrimmingCharactersInSet:whitespace];
		if ([key isEqualToString:@"cuts"])   numberOfCuts = [value integerValue];
		if ([key isEqualToString:@"move"])   maxMove      = fabs([value doubleValue]);
		if ([key isEqualToString:@"rotate"]) maxRotate    = fabs([value doubleValue]);
	}

	// Process the first master of the (already interpolated) instance font,
	// honouring any include:/exclude: glyph list, as in the SDK template.
	_checkSelection = NO;
	NSString *fontMasterId = [font fontMasterAtIndex:0].id;
	if (!fontMasterId) return;
	BOOL include = NO;
	NSError *error = nil;
	NSSet *glyphNames = getIncludeExcludeGlyphListFilter(arguments, &include, font, &error);
	for (GSGlyph *glyph in font.glyphs) {
		if (glyphNames && [glyphNames containsObject:glyph.name] != include) {
			continue;
		}
		GSLayer *layer = [glyph layerForId:fontMasterId];
		if (!layer) continue;
		[self applyFilterToLayer:layer
		            numberOfCuts:numberOfCuts
		                 maxMove:maxMove
		               maxRotate:maxRotate];
	}
}

#pragma mark - Core filter logic

/**
 Apply the full CutAndShake effect to a single @p layer.
 1. Make @p numberOfCuts random angled cuts.
 2. Shift each resulting path fragment by a random vector ≤ @p maxMove.
 3. Rotate each path fragment around its own centre by ≤ @p maxRotate degrees.
 */
- (void)applyFilterToLayer:(GSLayer *)layer
              numberOfCuts:(NSInteger)numberOfCuts
                   maxMove:(CGFloat)maxMove
                 maxRotate:(CGFloat)maxRotate {

	[self randomCutLayer:layer numberOfCuts:numberOfCuts];
	[self randomMovePaths:layer    maxMove:maxMove];
	[self randomRotatePaths:layer  maxRotate:maxRotate];
}

/**
 Make @p numberOfCuts random angled cuts through @p layer.
 Each cut either spans left-to-right or top-to-bottom; both endpoints get
 independently-random positions, producing diagonal cuts (matching the Python
 version).  The cut lines extend @c kGoodMeasure beyond the layer bounds so
 they cleanly intersect all paths.
 */
- (void)randomCutLayer:(GSLayer *)layer numberOfCuts:(NSInteger)numberOfCuts {
	Class knifeTool = CutPathsToolClass();
	if (!knifeTool || layer.paths.count == 0) return;

	NSRect b = layer.bounds;
	CGFloat lowestY    = NSMinY(b) - kGoodMeasure;
	CGFloat highestY   = NSMaxY(b) + kGoodMeasure;
	CGFloat leftmostX  = NSMinX(b) - kGoodMeasure;
	CGFloat rightmostX = NSMaxX(b) + kGoodMeasure;

	for (NSInteger i = 0; i < numberOfCuts; i++) {
		NSPoint p1, p2;
		if (arc4random_uniform(2) == 0) {
			// Roughly horizontal cut: spans left-to-right, both Y values independent → angled
			p1 = NSMakePoint(leftmostX,  [self randomBetween:lowestY and:highestY]);
			p2 = NSMakePoint(rightmostX, [self randomBetween:lowestY and:highestY]);
		} else {
			// Roughly vertical cut: spans top-to-bottom, both X values independent → angled
			p1 = NSMakePoint([self randomBetween:leftmostX and:rightmostX], lowestY);
			p2 = NSMakePoint([self randomBetween:leftmostX and:rightmostX], highestY);
		}
		[knifeTool cutPathsInLayer:layer forPoint:p1 endPoint:p2];
	}
}

/**
 Translate each path in @p layer by a random vector whose magnitude
 is at most @p maxMove (distributed uniformly per axis up to maxMove/√2
 so the maximum distance equals @p maxMove).
 */
- (void)randomMovePaths:(GSLayer *)layer maxMove:(CGFloat)maxMove {
	CGFloat halfRange = maxMove / sqrt(2.0);
	for (GSPath *path in layer.paths) {
		CGFloat dx = [self randomBetween:-halfRange and:halfRange];
		CGFloat dy = [self randomBetween:-halfRange and:halfRange];
		NSAffineTransform *t = [NSAffineTransform transform];
		[t translateXBy:dx yBy:dy];
		[self applyTransform:t toNodesOfPath:path];
	}
}

/**
 Rotate each path in @p layer by a random angle in [−maxRotate, +maxRotate]
 degrees around the path's own bounding-box centre.
 */
- (void)randomRotatePaths:(GSLayer *)layer maxRotate:(CGFloat)maxRotate {
	for (GSPath *path in layer.paths) {
		NSRect  b       = path.bounds;
		CGFloat cx      = NSMidX(b);
		CGFloat cy      = NSMidY(b);
		CGFloat degrees = [self randomBetween:-maxRotate and:maxRotate];

		NSAffineTransform *t = [NSAffineTransform transform];
		[t translateXBy:cx yBy:cy];
		[t rotateByDegrees:degrees];
		[t translateXBy:-cx yBy:-cy];
		[self applyTransform:t toNodesOfPath:path];
	}
}

/**
 Apply @p transform to every node in @p path.
 This mirrors what the Python wrapper's GSPath.applyTransform() does.
 */
- (void)applyTransform:(NSAffineTransform *)transform toNodesOfPath:(GSPath *)path {
	for (GSNode *node in path.nodes) {
		node.position = [transform transformPoint:node.position];
	}
}

#pragma mark - Helpers

/** Return a uniform random CGFloat in [minimum, maximum]. */
- (CGFloat)randomBetween:(CGFloat)minimum and:(CGFloat)maximum {
	CGFloat range  = maximum - minimum;
	CGFloat random = (CGFloat)arc4random() / (CGFloat)UINT32_MAX;
	return minimum + random * range;
}

@end
