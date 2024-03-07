//
//  UserProfileViewModel.swift
//  DemoApp
//
//  Created by Navnit Baldha on 07/03/24.
//

import Foundation
import Combine

class UserProfileViewModel: ObservableObject {

    @Published var userProfileList: [UserModel] = []
    private var cancellablr = Set<AnyCancellable>()
    let userNetworkService: UserNetworkService
    
    var serverErrorMessage: String = .empty

    init(userNetworkService: UserNetworkService = UserNetworkClient.shared) {
        self.userNetworkService = userNetworkService
    }

    enum Intent {
        case getUserData
        case updateCompanyName(name: String, currentModel: UserModel)
    }

    func trigger(by intent: Intent) {
        switch intent {
        case .getUserData:
            getUserDatabyAPICall()
        case .updateCompanyName(let name, let currentModel):
            updateCompanyName(name: name, userProfile: currentModel)
        }
    }
}

private extension UserProfileViewModel {

    func getUserDatabyAPICall() {
        userNetworkService.getUserData(url: APIEndPoints.user)
            .receive(on: DispatchQueue.main)
            .sink { completion in
                switch completion {
                case .finished:
                    debugPrint("Get currencies list...")
                case .failure(let error):
                    self.serverErrorMessage = ErrorMessage.serverErrorMessage
                }
            } receiveValue: { [weak self] userdata in
                self?.userProfileList = userdata
            }
            .store(in: &cancellablr)
    }

    func updateCompanyName(name: String, userProfile: UserModel) {
        if let row = self.userProfileList.firstIndex(where: {$0.id == userProfile.id}) {
            userProfileList[row].company?.name = name
        }
    }
}
