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
    os_model_namespace = openstudio.model
    openstudio_date = _openstudio_date_cpython
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
    os_model_namespace = openstudio
    openstudio_date = _openstudio_date_ironpython

# load all of the classes used by this package
# geometry classes
OSModel = os_model_namespace.Model
OSPoint3dVector = openstudio.Point3dVector
OSPoint3d = openstudio.Point3d
OSShadingSurfaceGroup = os_model_namespace.ShadingSurfaceGroup
OSShadingSurface = os_model_namespace.ShadingSurface
OSSubSurface = os_model_namespace.SubSurface
OSSurface = os_model_namespace.Surface
OSSpace = os_model_namespace.Space
OSThermalZone = os_model_namespace.ThermalZone
OSBuildingStory = os_model_namespace.BuildingStory
OSSurfacePropertyOtherSideCoefficients = os_model_namespace.SurfacePropertyOtherSideCoefficients
# schedule classes
OSScheduleTypeLimits = os_model_namespace.ScheduleTypeLimits
OSScheduleRuleset = os_model_namespace.ScheduleRuleset
OSScheduleRule = os_model_namespace.ScheduleRule
OSScheduleDay = os_model_namespace.ScheduleDay
OSScheduleFixedInterval = os_model_namespace.ScheduleFixedInterval
OSExternalFile = os_model_namespace.ExternalFile
OSScheduleFile = os_model_namespace.ScheduleFile
OSTime = openstudio.Time
OSTimeSeries = openstudio.TimeSeries
OSVector = openstudio.Vector
# material classes
OSMasslessOpaqueMaterial = os_model_namespace.MasslessOpaqueMaterial
OSStandardOpaqueMaterial = os_model_namespace.StandardOpaqueMaterial
OSRoofVegetation = os_model_namespace.RoofVegetation
OSSimpleGlazing = os_model_namespace.SimpleGlazing
OSStandardGlazing = os_model_namespace.StandardGlazing
OSGas = os_model_namespace.Gas
OSGasMixture = os_model_namespace.GasMixture
OSBlind = os_model_namespace.Blind
OSShade = os_model_namespace.Shade
OSWindowPropertyFrameAndDivider = os_model_namespace.WindowPropertyFrameAndDivider
# constructions classes
OSConstruction = os_model_namespace.Construction
OSMaterialVector = os_model_namespace.MaterialVector
OSShadingControl = os_model_namespace.ShadingControl
OSConstructionAirBoundary = os_model_namespace.ConstructionAirBoundary
OSZoneMixing = os_model_namespace.ZoneMixing
# construction set classes
OSDefaultConstructionSet = os_model_namespace.DefaultConstructionSet
OSDefaultSurfaceConstructions = os_model_namespace.DefaultSurfaceConstructions
OSDefaultSubSurfaceConstructions = os_model_namespace.DefaultSubSurfaceConstructions
# loads classes
OSPeopleDefinition = os_model_namespace.PeopleDefinition
OSPeople = os_model_namespace.People
OSLightsDefinition = os_model_namespace.LightsDefinition
OSLights = os_model_namespace.Lights
OSElectricEquipmentDefinition = os_model_namespace.ElectricEquipmentDefinition
OSElectricEquipment = os_model_namespace.ElectricEquipment
OSGasEquipmentDefinition = os_model_namespace.GasEquipmentDefinition
OSGasEquipment = os_model_namespace.GasEquipment
OSOtherEquipmentDefinition = os_model_namespace.OtherEquipmentDefinition
OSOtherEquipment = os_model_namespace.OtherEquipment
OSWaterUseEquipmentDefinition = os_model_namespace.WaterUseEquipmentDefinition
OSWaterUseEquipment = os_model_namespace.WaterUseEquipment
OSWaterUseConnections = os_model_namespace.WaterUseConnections
OSSpaceInfiltrationDesignFlowRate = os_model_namespace.SpaceInfiltrationDesignFlowRate
OSDesignSpecificationOutdoorAir = os_model_namespace.DesignSpecificationOutdoorAir
OSThermostatSetpointDualSetpoint = os_model_namespace.ThermostatSetpointDualSetpoint
OSZoneControlHumidistat = os_model_namespace.ZoneControlHumidistat
# ems classes
OSOutputVariable = os_model_namespace.OutputVariable
OSEnergyManagementSystemProgram = os_model_namespace.EnergyManagementSystemProgram
OSEnergyManagementSystemProgramCallingManager = \
    os_model_namespace.EnergyManagementSystemProgramCallingManager
OSEnergyManagementSystemSensor = os_model_namespace.EnergyManagementSystemSensor
OSEnergyManagementSystemActuator = os_model_namespace.EnergyManagementSystemActuator
OSEnergyManagementSystemConstructionIndexVariable = \
    os_model_namespace.EnergyManagementSystemConstructionIndexVariable
