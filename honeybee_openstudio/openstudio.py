"""Import OpenStudio SDK classes in different Python environments."""
import sys
import os
from honeybee_energy.config import folders as hbe_folders


if (sys.version_info >= (3, 0)):  # we are in cPython and can import normally
    import openstudio
    # load all of the classes used by this package
    # geometry classes
    OSModel = openstudio.model.Model
    OSPoint3dVector = openstudio.Point3dVector
    OSPoint3d = openstudio.Point3d
    OSShadingSurfaceGroup = openstudio.model.ShadingSurfaceGroup
    OSShadingSurface = openstudio.model.ShadingSurface
    OSSubSurface = openstudio.model.SubSurface
    OSSurface = openstudio.model.Surface
    OSSpace = openstudio.model.Space
    OSThermalZone = openstudio.model.ThermalZone
    OSBuildingStory = openstudio.model.BuildingStory
    OSSurfacePropertyOtherSideCoefficients = openstudio.model.SurfacePropertyOtherSideCoefficients
    # material classes
    OSMasslessOpaqueMaterial = openstudio.model.MasslessOpaqueMaterial
    OSStandardOpaqueMaterial = openstudio.model.StandardOpaqueMaterial
    OSRoofVegetation = openstudio.model.RoofVegetation
    OSSimpleGlazing = openstudio.model.SimpleGlazing
    OSStandardGlazing = openstudio.model.StandardGlazing
    OSGas = openstudio.model.Gas
    OSGasMixture = openstudio.model.GasMixture
    OSBlind = openstudio.model.Blind
    OSShade = openstudio.model.Shade
    OSWindowPropertyFrameAndDivider = openstudio.model.WindowPropertyFrameAndDivider

else:  # we are in IronPython and we must import the .NET bindings
    try:  # first see if OpenStudio has already been loaded
        import OpenStudio as openstudio
    except ImportError:
        try:
            import clr
        except ImportError as e:  # No .NET being used
            raise ImportError(
                'Failed to import CLR. OpenStudio SDK is unavailable.\n{}'.format(e))
        # check to be sure that the OpenStudio CSharp folder has been installed
        assert hbe_folders.openstudio_path is not None, \
            'No OpenStudio installation was found on this machine.'
        assert hbe_folders.openstudio_csharp_path is not None, \
            'No OpenStudio CSharp folder was found in the OpenStudio installation ' \
            'at:\n{}'.format(os.path.dirname(hbe_folders.openstudio_path))
        # add the OpenStudio DLL to the Common Language Runtime (CLR)
        os_dll = os.path.join(hbe_folders.openstudio_csharp_path, 'OpenStudio.dll')
        clr.AddReferenceToFileAndPath(os_dll)
        if hbe_folders.openstudio_csharp_path not in sys.path:
            sys.path.append(hbe_folders.openstudio_csharp_path)
        import OpenStudio as openstudio

    # load all of the classes used by this package
    # geometry classes
    OSModel = openstudio.Model
    OSPoint3dVector = openstudio.Point3dVector
    OSPoint3d = openstudio.Point3d
    OSShadingSurfaceGroup = openstudio.ShadingSurfaceGroup
    OSShadingSurface = openstudio.ShadingSurface
    OSSubSurface = openstudio.SubSurface
    OSSurface = openstudio.Surface
    OSSpace = openstudio.Space
    OSThermalZone = openstudio.ThermalZone
    OSBuildingStory = openstudio.BuildingStory
    OSSurfacePropertyOtherSideCoefficients = openstudio.SurfacePropertyOtherSideCoefficients
    # material classes
    OSMasslessOpaqueMaterial = openstudio.MasslessOpaqueMaterial
    OSStandardOpaqueMaterial = openstudio.StandardOpaqueMaterial
    OSRoofVegetation = openstudio.RoofVegetation
    OSSimpleGlazing = openstudio.SimpleGlazing
    OSStandardGlazing = openstudio.StandardGlazing
    OSGas = openstudio.Gas
    OSGasMixture = openstudio.GasMixture
    OSBlind = openstudio.Blind
    OSShade = openstudio.Shade
    OSWindowPropertyFrameAndDivider = openstudio.WindowPropertyFrameAndDivider
