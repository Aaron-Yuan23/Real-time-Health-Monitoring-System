#include <nuitrack/Nuitrack.h>
#include <iomanip>
#include <iostream>
#include <cstdlib>
using namespace tdv::nuitrack;
void showHelpInfo()
{
    std::cout << "Usage: nuitrack_console_sample [path/to/nuitrack.config]" << std::endl;
}



// Callback for the skeleton data update event
void onSkeletonUpdate(SkeletonData::Ptr skeletonData)
{
	int user_height = 0; //Intialized height value, used for height of skeleton calculation and fall distance
    if (!skeletonData)
    {
        // No skeleton data
        std::cout << "No skeleton data" << std::endl;
        return;
    }
    auto skeletons = skeletonData->getSkeletons();
    if (skeletons.empty())
    {
        // No skeletons
        return;
    }
//    auto joints = skeletons.joints; //maybe should be skeleton[0].joints?

    //Or try this:
    

        for (auto skeleton: skeletons)
    {
        //drawSkeleton(skeleton.joints);
        auto joints = skeleton.joints;

        // Insert rest of code below in this loop

		/*
		if (!joints) // Use different operator for no joints
		{
			// No joints
			std::cout << "The joints of the skeleton were not found" << std::endl;
			return;
		}
		*/

		std::cout << std::fixed << std::setprecision(3);

		std::cout << "Joint torso position: "
			"confidence = " << joints[JOINT_TORSO].confidence << ", "
			"x = " << joints[JOINT_TORSO].real.x << ", "
			"y = " << joints[JOINT_TORSO].real.y << ", "
			"z = " << joints[JOINT_TORSO].real.z << std::endl;

		std::cout << "Joint waist position: "
			"confidence = " << joints[JOINT_WAIST].confidence << ", "
			"x = " << joints[JOINT_WAIST].real.x << ", "
			"y = " << joints[JOINT_WAIST].real.y << ", "
			"z = " << joints[JOINT_WAIST].real.z << std::endl;

		//Other calculations for joint and waist
		std::cout << "Joint neck position: "
			"confidence = " << joints[JOINT_NECK].confidence << ", "
			"x = " << joints[JOINT_NECK].real.x << ", "
			"y = " << joints[JOINT_NECK].real.y << ", "
			"z = " << joints[JOINT_NECK].real.z << std::endl;

		//Algorithm checks if waist and neck and torso are in a lying down range
		
		
		int current_height = abs(joints[JOINT_HEAD].real.y - joints[JOINT_LEFT_ANKLE].real.y);
		if (current_height > user_height) {
			user_height = current_height;
		}

		int fall_range = user_height / 4; // Calculates safe distance for fall


		int distance = abs(joints[JOINT_NECK].real.y - joints[JOINT_WAIST].real.y);

		if (distance <= fall_range) {
			std::cout << "Fall Detected! \a" << std::endl;
			std::cin.get();
		}

		/*
		if (abs(joints[JOINT_NECK].real.y) >= abs((joints[JOINT_WAIST].real.y) - accuracy_range)
			||
			abs(joints[JOINT_NECK].real.y) <= (joints[JOINT_WAIST].real.y + accuracy_range)
			)


		{
			std::cout << "Fall Detected!" << std::endl;
		}
		*/
		/*
		if ((joints[JOINT_NECK].real.y >= (joints[JOINT_TORSO].real.y - accuracy_range)
			||
			joints[JOINT_NECK].real.y <= (joints[JOINT_TORSO].real.y + accuracy_range)
			)
			&&
			(joints[JOINT_WAIST].real.y >= (joints[JOINT_TORSO].real.y - accuracy_range)
				||
				joints[JOINT_WAIST].real.y <= (joints[JOINT_TORSO].real.y + accuracy_range)
				)) {
			std::cout << "Fall Detected!" << std::endl;
		}
		*/
    }
  


    

    // std::cout << "Right hand position: "
    //              "x = " << rightHand->xReal << ", "
    //              "y = " << rightHand->yReal << ", "
    //              "z = " << rightHand->zReal << std::endl;






/*    //Fall detection algorithm
    int accuracy_range = 100;



*/


}


/*
// Callback for the hand data update event
void onHandUpdate(HandTrackerData::Ptr handData)
{
    if (!handData)
    {
        // No hand data
        std::cout << "No hand data" << std::endl;
        return;
    }
    auto userHands = handData->getUsersHands();
    if (userHands.empty())
    {
        // No user hands
        return;
    }
    auto rightHand = userHands[0].rightHand;
    if (!rightHand)
    {
        // No right hand
        std::cout << "Right hand of the first user is not found" << std::endl;
        return;
    }
    std::cout << std::fixed << std::setprecision(3);
    std::cout << "Right hand position: "
                 "x = " << rightHand->xReal << ", "
                 "y = " << rightHand->yReal << ", "
                 "z = " << rightHand->zReal << std::endl;
}

*/


int main(int argc, char* argv[])
{
    showHelpInfo();
    std::string configPath = "";
    if (argc > 1)
        configPath = argv[1];
    // Initialize Nuitrack
    try
    {
        Nuitrack::init(configPath);
    }
    catch (const Exception& e)
    {
        std::cerr << "Can not initialize Nuitrack (ExceptionType: " << e.type() << ")" << std::endl;
        return EXIT_FAILURE;
    }
    
    // Create SkeletonTracker module, other required modules will be
    // created automatically
    auto skeletonTracker = SkeletonTracker::create();
    // Connect onSkeletonUpdate callback to receive skeleton tracking data
    skeletonTracker->connectOnUpdate(onSkeletonUpdate); //handTracker->connectOnUpdate(onHandUpdate);
    // Start Nuitrack
    try
    {
        Nuitrack::run();
    }
    catch (const Exception& e)
    {
        std::cerr << "Can not start Nuitrack (ExceptionType: " << e.type() << ")" << std::endl;
        return EXIT_FAILURE;
    }
    int errorCode = EXIT_SUCCESS;
    while (true)
    {
        try
        {
            // Wait for new skeleton tracking data
            Nuitrack::waitUpdate(skeletonTracker);
        }
        catch (LicenseNotAcquiredException& e)
        {
            std::cerr << "LicenseNotAcquired exception (ExceptionType: " << e.type() << ")" << std::endl;
            errorCode = EXIT_FAILURE;
            break;
        }
        catch (const Exception& e)
        {
            std::cerr << "Nuitrack update failed (ExceptionType: " << e.type() << ")" << std::endl;
            errorCode = EXIT_FAILURE;
        }
    }
    // Release Nuitrack
    try
    {
        Nuitrack::release();
    }
    catch (const Exception& e)
    {
        std::cerr << "Nuitrack release failed (ExceptionType: " << e.type() << ")" << std::endl;
        errorCode = EXIT_FAILURE;
    }
    return errorCode;
}
