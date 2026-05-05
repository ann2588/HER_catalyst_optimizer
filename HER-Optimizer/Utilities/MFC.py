import asyncio
from alicat import FlowController
import Utilities.portaccess as portaccess
#flow_controller = FlowController('COM5')
#print(flow_controller.get())
#flow_controller.set_gas('Ar')



#%%
import asyncio
from alicat import FlowController
#async def setup():
 #   async with FlowController('COM5') as flow_controller:
  #      await flow_controller.set_gas('Ar') # Set calibration as Ar
   #     await flow_controller.close()

#%%
async def n2on(flowrate=20):
    async with FlowController(portaccess.port_MFC) as Ar_controller:
    #await flow_controller.set_gas('Ar') # Set calibration as Ar
        await Ar_controller.set_flow_rate(flowrate)
        await Ar_controller.close()

async def n2off(flowrate=0):
    async with FlowController(portaccess.port_MFC) as Ar_controller:
    #await flow_controller.set_gas('Ar') # Set calibration as Ar
        await Ar_controller.set_flow_rate(flowrate)
        await Ar_controller.close()


#%%
async def H2on(flowrate=20):
    async with FlowController(portaccess.port_MFC_h2) as h2_controller:
    #await flow_controller.set_gas('Ar') # Set calibration as Ar
        await h2_controller.set_flow_rate(flowrate)
        await h2_controller.close()

async def H2off(flowrate=0):
    async with FlowController(portaccess.port_MFC_h2) as h2_controller:
    #await flow_controller.set_gas('Ar') # Set calibration as Ar
        await h2_controller.set_flow_rate(flowrate)
        await h2_controller.close()

#asyncio.run(MFCsetup())

#asyncio.run(MFC.close())
#asyncio.run(MFC.n2off())
#asyncio.run(MFC.n2on()) #Please assign desire flow rate
