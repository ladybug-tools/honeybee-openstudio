# coding=utf-8
"""Import OpenStudio SDK classes in different Python environments."""
import sys
import os
from honeybee_energy.config import folders as hbe_folders


def _openstudio_date_cpython(os_model, month, day):
    """Create an OpenStudio Date object."""
    year_desc = os_model.getYearDescription()
    return year_desc.makeDate(month, day)


def _openstudio_date_ironpython(os_model, month, day):
    """Get the YearDescription object from a Model."""
    model_year = os_model.calendarYear()
    model_year = model_year.get() if model_year.is_initialized() else 2009
    return openstudio.Date(openstudio.MonthOfYear(month), day, model_year)


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
    # schedule classes
    OSScheduleTypeLimits = openstudio.model.ScheduleTypeLimits
    OSScheduleRuleset = openstudio.model.ScheduleRuleset
    OSScheduleRule = openstudio.model.ScheduleRule
    OSScheduleDay = openstudio.model.ScheduleDay
    OSScheduleFixedInterval = openstudio.model.ScheduleFixedInterval
    OSExternalFile = openstudio.model.ExternalFile
    OSScheduleFile = openstudio.model.ScheduleFile
    OSDoubleVector = openstudio.DoubleVector
    OSTime = openstudio.Time
    OSTimeSeries = openstudio.TimeSeries
    OSVector = openstudio.Vector
    openstudio_date = _openstudio_date_cpython
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
    # constructions classes
    OSConstruction = openstudio.model.Construction
    OSMaterialVector = openstudio.model.MaterialVector
    OSShadingControl = openstudio.model.ShadingControl
    OSConstructionAirBoundary = openstudio.model.ConstructionAirBoundary
    OSZoneMixing = openstudio.model.ZoneMixing
    # construction set classes
    OSDefaultConstructionSet = openstudio.model.DefaultConstructionSet
    OSDefaultSurfaceConstructions = openstudio.model.DefaultSurfaceConstructions
    OSDefaultSubSurfaceConstructions = openstudio.model.DefaultSubSurfaceConstructions
    # ems classes
    OSEnergyManagementSystemProgram = openstudio.model.EnergyManagementSystemProgram
    OSEnergyManagementSystemProgramCallingManager = \
        openstudio.model.EnergyManagementSystemProgramCallingManager
    OSEnergyManagementSystemSensor = openstudio.model.EnergyManagementSystemSensor
    OSEnergyManagementSystemActuator = openstudio.model.EnergyManagementSystemActuator
    OSEnergyManagementSystemConstructionIndexVariable = \
        openstudio.model.EnergyManagementSystemConstructionIndexVariable

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
    # schedule classes
    OSScheduleTypeLimits = openstudio.ScheduleTypeLimits
    OSScheduleRuleset = openstudio.ScheduleRuleset
    OSScheduleRule = openstudio.ScheduleRule
    OSScheduleDay = openstudio.ScheduleDay
    OSScheduleFixedInterval = openstudio.ScheduleFixedInterval
    OSExternalFile = openstudio.ExternalFile
    OSScheduleFile = openstudio.ScheduleFile
    OSDoubleVector = openstudio.DoubleVector
    OSTime = openstudio.Time
    OSTimeSeries = openstudio.TimeSeries
    OSVector = openstudio.Vector
    openstudio_date = _openstudio_date_ironpython
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
    # constructions classes
    OSConstruction = openstudio.Construction
    OSMaterialVector = openstudio.MaterialVector
    OSShadingControl = openstudio.ShadingControl
    OSConstructionAirBoundary = openstudio.ConstructionAirBoundary
    OSZoneMixing = openstudio.ZoneMixing
    # construction set classes
    OSDefaultConstructionSet = openstudio.DefaultConstructionSet
    OSDefaultSurfaceConstructions = openstudio.DefaultSurfaceConstructions
    OSDefaultSubSurfaceConstructions = openstudio.DefaultSubSurfaceConstructions
    # ems classes
    OSEnergyManagementSystemProgram = openstudio.EnergyManagementSystemProgram
    OSEnergyManagementSystemProgramCallingManager = \
        openstudio.EnergyManagementSystemProgramCallingManager
    OSEnergyManagementSystemSensor = openstudio.EnergyManagementSystemSensor
    OSEnergyManagementSystemActuator = openstudio.EnergyManagementSystemActuator
    OSEnergyManagementSystemConstructionIndexVariable = \
        openstudio.EnergyManagementSystemConstructionIndexVariable
